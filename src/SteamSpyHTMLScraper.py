"""
SteamSpyHTMLScraper - Fallback scraper that parses steamspy.com HTML directly.

Use this when the SteamSpy API (/api.php) returns "Connection failed: Too many connections".
The homepage renders full trending/recent game tables even when the API backend is down.

Mirrors SteamSpyScraper exactly:
  - Same BaseScraper interface and async context manager
  - Same output files: steamspy_data.jsonl, scraped_appids.txt, steamspy_errors.log, metadata.json
  - Same progress/resume logic
  - Same appid 999999 filter

Data differences vs normal API run:
  - Pulls from the homepage trending + recent tables (up to ~200 apps)
  - Does NOT paginate through all apps (homepage only shows ~200)
  - Missing fields that only appdetails returns: developer, publisher,
    positive/negative review counts, userscore, avg/median playtime, ccu
  - Those fields are filled with None so schema stays consistent
  - If the API recovers mid-run, appdetails is attempted and used when available
"""

import asyncio
import json
import re
from typing import Any, Dict, List, Optional, Tuple

import aiohttp
from bs4 import BeautifulSoup

from src.BaseScraper import BaseScraper
from src.FileSystem import FileSystem
from src.RateLimiter import RateLimiter

# Fields present in a normal appdetails response.
# Any field we can't get from HTML is set to None so consumers
# never encounter a KeyError when the schema switches between sources.
_APPDETAILS_SCHEMA = {
    "appid": None,
    "name": None,
    "developer": None,        # not on homepage
    "publisher": None,        # not on homepage
    "score_rank": "",
    "positive": None,         # not on homepage
    "negative": None,         # not on homepage
    "userscore": None,        # not on homepage
    "owners": None,
    "average_forever": None,  # not on homepage
    "average_2weeks": None,   # not on homepage
    "median_forever": None,   # not on homepage
    "median_2weeks": None,    # not on homepage
    "ccu": None,              # not on homepage
    "price": None,
    "initialprice": None,
    "discount": None,
    "tags": {},
    "languages": None,
    "genre": None,
}


def _parse_owners(owners_str: str) -> Optional[str]:
    """Normalise owners column from HTML e.g. '0 .. 20,000' to match API format."""
    return owners_str.strip() if owners_str else None


def _parse_price(price_str: str) -> Optional[int]:
    """Convert '$24.99' -> 2499 (cents), matching appdetails integer format."""
    price_str = price_str.strip()
    if not price_str or price_str in ("N/A", "Free", "Free to Play"):
        return None
    try:
        return int(round(float(price_str.replace("$", "").replace(",", "")) * 100))
    except ValueError:
        return None


def _parse_score(score_str: str) -> Tuple[str, Optional[int]]:
    """Parse 'N/A (N/A/83%)' -> score_rank='', metascore=83."""
    score_str = score_str.strip()
    metascore = None
    m = re.search(r'/(\d+)%', score_str)
    if m:
        metascore = int(m.group(1))
    score_rank = re.sub(r'\s*\(.*?\)', '', score_str).strip()
    if score_rank in ("N/A", ""):
        score_rank = ""
    return score_rank, metascore


def _parse_playtime(pt_str: str) -> Tuple[Optional[int], Optional[int]]:
    """
    Parse 'HH:MM (HH:MM)' -> (average_minutes, median_minutes).
    Outer value = average_forever, inner = median_forever (matching API convention).
    """
    if not pt_str or pt_str.strip() == "":
        return None, None
    m = re.match(r'(\d+):(\d+)\s*\((\d+):(\d+)\)', pt_str.strip())
    if not m:
        return None, None
    avg = int(m.group(1)) * 60 + int(m.group(2))
    med = int(m.group(3)) * 60 + int(m.group(4))
    return avg, med


def _parse_table(soup: BeautifulSoup, tab_id: str) -> List[Dict[str, Any]]:
    """
    Parse a homepage tab's <table> and return a list of partial app dicts.

    Homepage table columns:
      Trending (6 cols): #, Game (link), Release date, Price, Score, Owners
      Recent   (7 cols): #, Game (link), Release date, Price, Score, Owners, Playtime
    """
    tab = soup.find("div", {"id": tab_id})
    if not tab:
        return []

    table = tab.find("table")
    if not table:
        return []

    apps = []
    for row in table.find_all("tr")[1:]:  # skip header row
        cols = row.find_all("td")
        if not cols:
            continue

        # Column 1: game link -> appid + name
        link_tag = cols[1].find("a", href=True) if len(cols) > 1 else None
        if not link_tag:
            continue
        href = link_tag.get("href", "")
        m = re.search(r'/app/(\d+)', href)
        if not m:
            continue
        appid = int(m.group(1))
        if appid == 999999:
            continue

        name = link_tag.get_text(strip=True)
        release_date = cols[2].get_text(strip=True) if len(cols) > 2 else None
        price_cents = _parse_price(cols[3].get_text(strip=True) if len(cols) > 3 else "")
        score_rank, metascore = _parse_score(cols[4].get_text(strip=True) if len(cols) > 4 else "")
        owners_raw = cols[5].get_text(strip=True) if len(cols) > 5 else None

        avg_pt, med_pt = None, None
        if len(cols) > 6:
            avg_pt, med_pt = _parse_playtime(cols[6].get_text(strip=True))

        app = {
            **_APPDETAILS_SCHEMA,
            "appid": appid,
            "name": name,
            "score_rank": score_rank,
            "owners": _parse_owners(owners_raw),
            "price": price_cents,
            "initialprice": price_cents,
            "discount": 0,
            "average_forever": avg_pt,
            "median_forever": med_pt,
            "_source": "html_fallback",
            "_release_date": release_date,
            "_tab": tab_id,
        }
        if metascore is not None:
            app["_metascore"] = metascore

        apps.append(app)

    return apps


class SteamSpyHTMLScraper(BaseScraper):
    """
    Fallback scraper that reads steamspy.com homepage HTML when the API is down.
    Matches SteamSpyScraper's interface, file outputs, and behaviour exactly.
    """

    HOMEPAGE_URL = "https://steamspy.com/"
    TABS = ["tab-trending", "tab-recent", "tab-total"]

    def __init__(
        self,
        filesystem: FileSystem,
        page_delay: float = 1.0,
        app_delay: float = 0.1,
        suppress_output: bool = False,
        try_api_fallback: bool = True,
    ):
        """
        Args:
            filesystem:       FileSystem instance (same as SteamSpyScraper).
            page_delay:       Delay after homepage fetch before enrichment pass.
            app_delay:        Per-app rate limit for optional appdetails enrichment.
            suppress_output:  Mirror BaseScraper flag.
            try_api_fallback: If True, attempt appdetails for each app - useful if
                              the API recovers mid-run. Set False for pure-HTML mode.
        """
        super().__init__(filesystem, suppress_output)
        self.base_url = "https://steamspy.com/api.php"
        self.page_delay = page_delay
        self.rate_limiter = RateLimiter(app_delay)
        self.try_api_fallback = try_api_fallback

        # Identical file names to SteamSpyScraper
        self.output_file = "steamspy_data.jsonl"
        self.progress_file = "scraped_appids.txt"
        self.error_file = "steamspy_errors.log"

    async def _fetch_homepage(self) -> Optional[str]:
        """Fetch the steamspy.com homepage HTML."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml",
        }
        try:
            async with self.session.get(
                self.HOMEPAGE_URL, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status != 200:
                    self.log_error(f"Homepage HTTP {resp.status}", self.error_file)
                    return None
                return await resp.text()
        except Exception as e:
            self.log_error(f"Homepage fetch failed: {e}", self.error_file)
            return None

    async def _try_appdetails(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Attempt to enrich an app via the appdetails API endpoint.
        Returns None silently if the API is still down - HTML data is used instead.
        """
        params = {"request": "appdetails", "appid": appid}
        try:
            async with self.session.get(
                self.base_url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None
                text = await resp.text()
                stripped = text.strip()
                if not (stripped.startswith("{") or stripped.startswith("[")):
                    return None  # still returning plain-text error
                data = json.loads(stripped)
                if isinstance(data, dict) and data.get("appid") and data["appid"] != 999999:
                    return data
                return None
        except Exception:
            return None

    def _deduplicate(self, apps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate appids, keeping first occurrence (trending tab wins)."""
        seen = set()
        result = []
        for app in apps:
            aid = app["appid"]
            if aid not in seen:
                seen.add(aid)
                result.append(app)
        return result

    async def scrape(self, progress_callback=None) -> int:
        """
        Scrape SteamSpy data from homepage HTML.

        Returns:
            Number of apps written to steamspy_data.jsonl
        """
        scraped_ids = self.load_progress(self.progress_file)
        total_scraped = 0

        # Step 1: fetch homepage
        self._print("Fetching steamspy.com homepage (HTML fallback mode)...")
        html = await self._fetch_homepage()

        if not html:
            self._print("Could not fetch homepage. Aborting.")
            self.save_metadata({"pages_scraped": 0, "apps_scraped": 0,
                                "mode": "html_fallback", "error": "homepage_fetch_failed"})
            return 0

        # Step 2: parse all tabs
        soup = BeautifulSoup(html, "html.parser")
        all_apps: List[Dict[str, Any]] = []

        for tab_id in self.TABS:
            tab_apps = _parse_table(soup, tab_id)
            self._print(f"  {tab_id}: {len(tab_apps)} apps found")
            all_apps.extend(tab_apps)

        all_apps = self._deduplicate(all_apps)
        self._print(f"Total unique apps from HTML: {len(all_apps)}")

        if not all_apps:
            self._print("No apps parsed from HTML. Page structure may have changed.")
            self.log_error("HTML parse returned 0 apps", self.error_file)
            self.save_metadata({"pages_scraped": 0, "apps_scraped": 0,
                                "mode": "html_fallback", "error": "html_parse_empty"})
            return 0

        if self.page_delay > 0:
            await asyncio.sleep(self.page_delay)

        # Step 3: optionally enrich via appdetails
        for i, app in enumerate(all_apps):
            appid = app["appid"]

            if progress_callback:
                progress_callback(i, len(all_apps), "HTML fallback")

            if str(appid) in scraped_ids:
                continue

            enriched = None
            if self.try_api_fallback:
                async with self.rate_limiter:
                    enriched = await self._try_appdetails(appid)

            final = enriched if enriched else app

            if final.get("appid") != 999999:
                self.fs.append_jsonl(final, self.output_file)
                self.save_progress(str(appid), self.progress_file)
                total_scraped += 1

        self._print(f"\nHTML fallback complete: {total_scraped} apps saved")
        self.save_metadata({
            "pages_scraped": 1,
            "apps_scraped": total_scraped,
            "mode": "html_fallback",
            "tabs_parsed": self.TABS,
        })

        return total_scraped