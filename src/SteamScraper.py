"""SteamScraper - Scrapes live official Steam data (reviews + concurrent players).

Replaces the frozen SteamSpy signals (review counts, CCU) with data pulled
straight from Steam's own endpoints:

  - api.steampowered.com/IStoreBrowseService/GetItems -> name, store
    visibility, review_count, percent_positive, review_score(_label);
    batched, REVIEWS_BATCH apps per request
  - api.steampowered.com/ISteamUserStats/GetNumberOfCurrentPlayers -> player_count

(store.steampowered.com/appreviews used to supply reviews; by 2026-11 it
302-redirects to the store homepage.)

Review figures are Steam's "filtered" summary (review bombs removed), and
percent_positive is a whole number, so exact positive/negative counts are
not available.

The app universe is the current SteamSpy catalog. On a CI runner Data/ is
empty (gitignored), so the appid list is fetched from the newest GitHub
release asset (steamspy_scraped_appids.txt); STEAM_APPIDS_FILE overrides this
with a local file for dev/testing.
"""
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter

GITHUB_REPO = "Icewav3/SteamScraping"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# Asset carrying the SteamSpy appid universe (prefixed on newer releases,
# unprefixed on the earliest ones). The newest release wins either way.
APPIDS_ASSET_NAMES = ("steamspy_scraped_appids.txt", "scraped_appids.txt")
# Sentinel appid SteamSpy sometimes emits; never a real app.
SENTINEL_APPID = 999999
# 429 backoff schedule (seconds); after these are exhausted the request fails.
BACKOFFS = (30, 60, 120)
# GetItems handled 200 ids per request in testing (2026-11-07); 100 leaves margin.
REVIEWS_BATCH = 100
# GetItems item.success value for an app that resolved normally.
ITEM_OK = 1

# A run fails (so the workflow retries) when any of these are breached.
# Missing: share of the universe with no row at all (some appids are truly dead).
MAX_MISSING_FRACTION = 0.01
# Coverage: share of the day's rows carrying the field. Delisted apps
# legitimately lack both, but a collapse means an endpoint broke.
MIN_REVIEW_COVERAGE = 0.5
MIN_PLAYER_COVERAGE = 0.5


class SteamScraper(BaseScraper):
    """Scraper for live official Steam review + player-count data."""

    def __init__(self, filesystem: FileSystem, api_delay: float = 0.3,
                 suppress_output: bool = False):
        super().__init__(filesystem, suppress_output)
        self.items_url = "https://api.steampowered.com/IStoreBrowseService/GetItems/v1/"
        self.players_url = ("https://api.steampowered.com/ISteamUserStats/"
                            "GetNumberOfCurrentPlayers/v1/")
        # Both endpoints live on api.steampowered.com, so they share a limiter.
        self.limiter = RateLimiter(api_delay)

        self.output_file = "steam_data.jsonl"
        self.progress_file = "steam_scraped_appids.txt"
        self.error_file = "steam_errors.log"

        self.apps_total = 0
        self.apps_missing = 0
        self.review_coverage = 0.0
        self.player_coverage = 0.0

    @property
    def is_complete(self) -> bool:
        """True when the day covers enough apps, with both endpoints working."""
        return (self.apps_total > 0
                and self.apps_missing <= self.apps_total * MAX_MISSING_FRACTION
                and self.review_coverage >= MIN_REVIEW_COVERAGE
                and self.player_coverage >= MIN_PLAYER_COVERAGE)

    # ------------------------------------------------------------ app universe

    def _parse_appids(self, text: str) -> List[int]:
        """Parse an appid-per-line progress file, dropping dups and the sentinel."""
        seen = set()
        appids = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                appid = int(line)
            except ValueError:
                continue
            if appid == SENTINEL_APPID or appid in seen:
                continue
            seen.add(appid)
            appids.append(appid)
        return appids

    async def _download_text(self, url: str) -> str:
        async with self.session.get(url) as resp:
            resp.raise_for_status()
            return await resp.text()

    async def _fetch_appid_universe(self) -> List[int]:
        """Fetch the newest release's SteamSpy appid list from GitHub.

        Releases are keyed by TAG NAME (dates); creation order lies for
        backfilled days, so we sort tags descending and take the newest
        release that carries an appid asset.
        """
        api = f"https://api.github.com/repos/{GITHUB_REPO}/releases?per_page=100&page="
        # Runners share IPs, so the anonymous 60/hr limit is unreliable on CI.
        token = os.getenv("GITHUB_TOKEN")
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        releases: List[tuple] = []  # (tag, {asset_name: url})
        page = 1
        while True:
            async with self.session.get(api + str(page), headers=headers) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"GitHub API HTTP {resp.status} listing releases")
                batch = await resp.json()
            if not batch:
                break
            for rel in batch:
                tag = rel.get("tag_name", "")
                if DATE_RE.match(tag):
                    assets = {a["name"]: a["browser_download_url"]
                              for a in rel.get("assets", [])}
                    releases.append((tag, assets))
            page += 1

        for tag, assets in sorted(releases, key=lambda r: r[0], reverse=True):
            for name in APPIDS_ASSET_NAMES:
                if name in assets:
                    self._print(f"Using appid universe from release {tag} ({name})")
                    return self._parse_appids(await self._download_text(assets[name]))
        raise RuntimeError("no release asset with a SteamSpy appid list found")

    async def _load_appids(self) -> List[int]:
        override = os.getenv("STEAM_APPIDS_FILE")
        if override:
            self._print(f"Using appid universe from {override}")
            return self._parse_appids(Path(override).read_text(encoding="utf-8"))
        return await self._fetch_appid_universe()

    # --------------------------------------------------------------- fetching

    async def _fetch(self, url: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """GET JSON with rate limiting and 429 exponential backoff.

        Returns parsed JSON, or None on HTTP/network failure (incl. 404 and
        429 that survives every backoff). The backoff sleep happens outside
        the limiter so it never holds the shared lock.
        """
        for backoff in (None, *BACKOFFS):
            if backoff is not None:
                self._print(f"429 on {url}, backing off {backoff}s")
                await asyncio.sleep(backoff)
            async with self.limiter:
                try:
                    async with self.session.get(url, params=params) as resp:
                        if resp.status == 200:
                            return await resp.json(content_type=None)
                        if resp.status == 429:
                            continue  # retry after backoff on next iteration
                        if resp.status == 404:
                            return None  # delisted/unknown app — caller nulls it
                        self.log_error(f"HTTP {resp.status}: {url}", self.error_file)
                        return None
                except Exception as e:
                    self.log_error(f"{url}: {e}", self.error_file)
                    return None
        self.log_error(f"429 backoff exhausted: {url}", self.error_file)
        return None

    async def _fetch_items(self, appids: List[int]) -> Optional[Dict[int, Dict[str, Any]]]:
        """Store items for a batch, keyed by appid; None if the request failed."""
        query = {
            "ids": [{"appid": a} for a in appids],
            "context": {"language": "english", "country_code": "US"},
            "data_request": {"include_reviews": True},
        }
        data = await self._fetch(self.items_url, {"input_json": json.dumps(query)})
        items = (data or {}).get("response", {}).get("store_items")
        if not isinstance(items, list):
            self.log_error(f"GetItems: no store_items for batch starting {appids[0]}",
                           self.error_file)
            return None
        return {item["id"]: item for item in items if isinstance(item.get("id"), int)}

    async def _fetch_players(self, appid: int) -> Optional[int]:
        """Current players, or None for delisted/unknown apps and failures."""
        data = await self._fetch(self.players_url, {"appid": appid})
        response = (data or {}).get("response", {})
        if response.get("result") == 1 and "player_count" in response:
            return response["player_count"]
        return None

    @staticmethod
    def _record(appid: int, item: Dict[str, Any], players: Optional[int]) -> Dict[str, Any]:
        ok = item.get("success") == ITEM_OK
        summary = ((item.get("reviews") or {}).get("summary_filtered") or {}) if ok else {}
        return {
            "appid": appid,
            "name": item.get("name") or None,
            "visible": item.get("visible"),
            # Set on some secondary listings (e.g. a multiplayer appid) whose
            # reviews live on the parent; such rows show review_count 0.
            "parent_appid": (item.get("related_items") or {}).get("parent_appid"),
            "review_count": summary.get("review_count"),
            "percent_positive": summary.get("percent_positive"),
            "review_score": summary.get("review_score"),
            "review_score_label": summary.get("review_score_label"),
            "player_count": players,
        }

    # ---------------------------------------------------------------- scrape

    def _day_rows(self) -> Dict[int, Dict[str, Any]]:
        """Every row written today, across all attempts (last write wins)."""
        path = self.fs.get_output_path(self.output_file)
        rows: Dict[int, Dict[str, Any]] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    rows[row["appid"]] = row
        return rows

    def _assess(self, appids: List[int]) -> None:
        """Judge the whole day, not just this attempt, so retries add up."""
        rows = self._day_rows()
        done = [rows[a] for a in appids if a in rows]
        self.apps_total = len(appids)
        self.apps_missing = len(appids) - len(done)
        if done:
            self.review_coverage = sum(r["review_count"] is not None for r in done) / len(done)
            self.player_coverage = sum(r["player_count"] is not None for r in done) / len(done)

    async def scrape(self, progress_callback=None) -> int:
        """Scrape live Steam data for the whole appid universe."""
        appids = await self._load_appids()
        self._print(f"Loaded {len(appids)} appids")
        scraped_ids = self.load_progress(self.progress_file)
        todo = [a for a in appids if str(a) not in scraped_ids]
        total_scraped = 0

        for start in range(0, len(todo), REVIEWS_BATCH):
            batch = todo[start:start + REVIEWS_BATCH]
            if progress_callback:
                progress_callback(start, len(todo), "Steam")

            items = await self._fetch_items(batch)
            if items is None:
                continue  # whole batch missing; a retry re-attempts it

            for appid in batch:
                item = items.get(appid)
                if item is None:
                    self.log_error(f"GetItems omitted appid {appid}", self.error_file)
                    continue
                record = self._record(appid, item, await self._fetch_players(appid))
                self.fs.append_jsonl(record, self.output_file)
                self.save_progress(str(appid), self.progress_file)
                total_scraped += 1

        self._assess(appids)
        self.save_metadata({"apps_total": self.apps_total, "apps_scraped": total_scraped,
                            "apps_missing": self.apps_missing,
                            "review_coverage": round(self.review_coverage, 4),
                            "player_coverage": round(self.player_coverage, 4)},
                           "steam_metadata.json")
        return total_scraped


if __name__ == "__main__":
    import sys

    async def main():
        """Run scraper with environment configuration."""
        fs = FileSystem("Data", "SteamScraper")
        api_delay = float(os.getenv("STEAM_API_DELAY", "0.3"))

        async with SteamScraper(fs, api_delay=api_delay) as scraper:
            total = await scraper.scrape()
            print(f"Scraped {total} apps this attempt; "
                  f"{scraper.apps_missing}/{scraper.apps_total} still missing; "
                  f"review coverage {scraper.review_coverage:.1%}, "
                  f"player coverage {scraper.player_coverage:.1%}")
            return scraper.is_complete

    try:
        sys.exit(0 if asyncio.run(main()) else 1)
    except Exception as e:
        print(f"✗ Scraper failed: {e}", file=sys.stderr)
        sys.exit(1)
