# src/ReleaseSync.py
"""ReleaseSync - Downloads daily data snapshots from GitHub release assets.

The scrape workflows upload each day's output as assets on a release tagged
YYYY-MM-DD. This tool mirrors those assets into the local Data/ tree so the
full history can be queried locally.

Releases are keyed by TAG NAME, never by GitHub's creation order — backfilled
old dates are uploaded out of chronological order, so creation order lies.

Asset naming has drifted over time; everything is normalized on download to
the current layout: Data/<date>/<ScraperName>/<prefix>_<file>.

Usage:
    uv run python -m src.ReleaseSync                  # sync everything missing
    uv run python -m src.ReleaseSync --since 2026-06-01
    uv run python -m src.ReleaseSync --dry-run
"""
import asyncio
import json
import re
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import aiohttp

DEFAULT_REPO = "Icewav3/SteamScraping"
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Maps every asset name ever used by the workflows to (scraper dir, normalized name).
# Unprefixed names come from early releases before FileSystem added prefixes.
ASSET_MAP = {
    "steamspy_data.jsonl":          ("SteamSpyScraper", "steamspy_data.jsonl"),
    "steamspy_scraped_appids.txt":  ("SteamSpyScraper", "steamspy_scraped_appids.txt"),
    "steamspy_metadata.json":       ("SteamSpyScraper", "steamspy_metadata.json"),
    "steamspy_errors.log":          ("SteamSpyScraper", "steamspy_errors.log"),
    "scraped_appids.txt":           ("SteamSpyScraper", "steamspy_scraped_appids.txt"),
    "metadata.json":                ("SteamSpyScraper", "steamspy_metadata.json"),
    "igdb_data.jsonl":              ("IGDBScraper", "igdb_data.jsonl"),
    "igdb_scraped_game_ids.txt":    ("IGDBScraper", "igdb_scraped_game_ids.txt"),
    "igdb_metadata.json":           ("IGDBScraper", "igdb_metadata.json"),
    "igdb_errors.log":              ("IGDBScraper", "igdb_errors.log"),
    "igdb_steam_links.jsonl":       ("IGDBScraper", "igdb_steam_links.jsonl"),
    "scraped_game_ids.txt":         ("IGDBScraper", "igdb_scraped_game_ids.txt"),
    "steam_data.jsonl":             ("SteamScraper", "steam_data.jsonl"),
    "steam_scraped_appids.txt":     ("SteamScraper", "steam_scraped_appids.txt"),
    "steam_metadata.json":          ("SteamScraper", "steam_metadata.json"),
    "steam_errors.log":             ("SteamScraper", "steam_errors.log"),
}


@dataclass
class Asset:
    name: str
    size: int
    url: str  # browser_download_url (not API rate limited)


@dataclass
class SyncStats:
    downloaded: int = 0
    skipped: int = 0
    unknown_assets: List[str] = field(default_factory=list)


class ReleaseSync:
    """Mirrors GitHub release assets into the local Data/ tree."""

    def __init__(self, data_dir: str = "Data", repo: str = DEFAULT_REPO,
                 concurrency: int = 4):
        self.data_dir = Path(data_dir)
        self.repo = repo
        self.api_base = f"https://api.github.com/repos/{repo}"
        self.semaphore = asyncio.Semaphore(concurrency)

    async def list_releases(self, session: aiohttp.ClientSession) -> Dict[str, List[Asset]]:
        """Return {date_tag: [assets]} for all date-tagged releases, sorted by tag."""
        releases: Dict[str, List[Asset]] = {}
        page = 1
        while True:
            url = f"{self.api_base}/releases?per_page=100&page={page}"
            async with session.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"GitHub API HTTP {resp.status} listing releases "
                                       f"(unauthenticated rate limit is 60/hr)")
                batch = await resp.json()
            if not batch:
                break
            for rel in batch:
                tag = rel["tag_name"]
                if DATE_RE.match(tag):
                    releases[tag] = [
                        Asset(a["name"], a["size"], a["browser_download_url"])
                        for a in rel["assets"]
                    ]
            page += 1
        return dict(sorted(releases.items()))

    def _dest_path(self, date: str, asset_name: str) -> Optional[Path]:
        mapped = ASSET_MAP.get(asset_name)
        if mapped is None:
            return None
        scraper_dir, normalized = mapped
        return self.data_dir / date / scraper_dir / normalized

    def _needs_download(self, dest: Path, asset: Asset) -> bool:
        return not dest.exists() or dest.stat().st_size != asset.size

    async def _download(self, session: aiohttp.ClientSession, asset: Asset,
                        dest: Path) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        async with self.semaphore:
            async with session.get(asset.url) as resp:
                resp.raise_for_status()
                fd, tmp = tempfile.mkstemp(dir=dest.parent, prefix=f".{dest.name}.",
                                           suffix=".tmp")
                try:
                    with open(fd, "wb") as f:
                        async for chunk in resp.content.iter_chunked(1 << 16):
                            f.write(chunk)
                    Path(tmp).replace(dest)
                except BaseException:
                    Path(tmp).unlink(missing_ok=True)
                    raise

    async def sync(self, since: Optional[str] = None, until: Optional[str] = None,
                   dry_run: bool = False,
                   progress_callback=None) -> SyncStats:
        """Download all missing/changed assets. Returns stats."""
        stats = SyncStats()
        timeout = aiohttp.ClientTimeout(total=600)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            releases = await self.list_releases(session)

            work = []  # (asset, dest)
            for date, assets in releases.items():
                if (since and date < since) or (until and date > until):
                    continue
                for asset in assets:
                    dest = self._dest_path(date, asset.name)
                    if dest is None:
                        stats.unknown_assets.append(f"{date}/{asset.name}")
                        continue
                    if self._needs_download(dest, asset):
                        work.append((asset, dest))
                    else:
                        stats.skipped += 1

            if dry_run:
                for asset, dest in work:
                    print(f"would download {dest} ({asset.size / 1e6:.1f} MB)")
                stats.downloaded = len(work)
                return stats

            for i, (asset, dest) in enumerate(work):
                if progress_callback:
                    progress_callback(i, len(work), dest.parent.parent.name)
                await self._download(session, asset, dest)
                stats.downloaded += 1

        return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Sync data snapshots from GitHub releases")
    parser.add_argument("--repo", default=DEFAULT_REPO)
    parser.add_argument("--data-dir", default="Data")
    parser.add_argument("--since", help="Earliest date tag to sync (YYYY-MM-DD)")
    parser.add_argument("--until", help="Latest date tag to sync (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    from tqdm import tqdm

    async def main() -> SyncStats:
        sync = ReleaseSync(args.data_dir, args.repo)
        bar = tqdm(desc="Syncing", unit="file")

        def progress(i, total, label):
            bar.total = total
            bar.n = i
            bar.set_postfix_str(label)
            bar.refresh()

        try:
            return await sync.sync(since=args.since, until=args.until,
                                   dry_run=args.dry_run, progress_callback=progress)
        finally:
            bar.close()

    try:
        stats = asyncio.run(main())
        print(f"✓ downloaded {stats.downloaded}, up-to-date {stats.skipped}")
        if stats.unknown_assets:
            print(f"⚠ unrecognized assets (skipped): {stats.unknown_assets}", file=sys.stderr)
        sys.exit(0)
    except Exception as e:
        print(f"✗ sync failed: {e}", file=sys.stderr)
        sys.exit(1)
