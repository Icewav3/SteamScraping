"""SteamSpyScraper - Scrapes game data from SteamSpy API."""
import asyncio
from typing import Dict, Any, Optional
from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter

# A full request=all page; only the last page may legitimately hold fewer.
FULL_PAGE = 1000


class SteamSpyScraper(BaseScraper):
    """Scraper for SteamSpy API."""
    
    def __init__(self, filesystem: FileSystem, pages: int = 10,
                 page_delay: float = 1.0, app_delay: float = 0.1,
                 suppress_output: bool = False):
        super().__init__(filesystem, suppress_output)
        self.base_url = "https://steamspy.com/api.php"
        self.pages = pages
        self.page_delay = page_delay
        self.rate_limiter = RateLimiter(app_delay)
        
        self.output_file = "steamspy_data.jsonl"
        self.progress_file = "scraped_appids.txt"
        self.error_file = "steamspy_errors.log"
        self.pages_completed = 0
        self.page_log = []
        self._last_headers = {}
    
    async def _request(self, request_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make API request."""
        params = {"request": request_type, **kwargs}
        
        try:
            async with self.session.get(self.base_url, params=params) as resp:
                self._last_headers = resp.headers
                if resp.status != 200:
                    self.log_error(f"HTTP {resp.status}: {request_type}", self.error_file)
                    return None
                return await resp.json()
        except Exception as e:
            self.log_error(f"{request_type}: {e}", self.error_file)
            return None
    
    async def scrape(self, progress_callback=None) -> int:
        """Scrape SteamSpy data."""
        scraped_ids = self.load_progress(self.progress_file)
        total_scraped = 0
        
        for page in range(self.pages):
            self._print(f"\nFetching page {page}...")
            self._last_headers = {}
            apps = await self._request("all", page=page)
            h = self._last_headers
            # Cloudflare serves its saved copy (STALE) when SteamSpy's server is down
            self.page_log.append({"page": page, "ok": bool(apps), "apps": len(apps or {}),
                                  "cf_cache_status": h.get("cf-cache-status"),
                                  "age": h.get("age"), "last_modified": h.get("last-modified")})
            
            if not apps:
                self._print(f"Page {page} failed or empty; skipping (see {self.error_file})")
                continue
            
            app_ids = [int(aid) for aid in apps.keys()]
            
            for i, appid in enumerate(app_ids):
                if progress_callback:
                    progress_callback(i, len(app_ids), f"Page {page}")
                
                if str(appid) in scraped_ids:
                    continue
                
                async with self.rate_limiter:
                    data = await self._request("appdetails", appid=appid)
                
                if data and data.get("appid") != 999999:
                    self.fs.append_jsonl(data, self.output_file)
                    self.save_progress(str(appid), self.progress_file)
                    total_scraped += 1
            
            self.pages_completed += 1
            self._print(f"Page {page}: scraped {len(app_ids)} apps")
            if self.page_delay > 0:
                await asyncio.sleep(self.page_delay)
        
        self.save_metadata({"pages_scraped": self.pages_completed, "apps_scraped": total_scraped,
                            "pages": self.page_log})
        return total_scraped

    def exit_code(self) -> int:
        """0 if the day has any records, else 1. Degraded pages only warn.

        SteamSpy's origin is often down, and Cloudflare's cached copies can be
        error pages; no retry can fix that the same day, so it must not fail the run.
        """
        records = len(self.load_progress(self.progress_file))  # the whole day, not this attempt
        missing = [p["page"] for p in self.page_log if not p["ok"]]
        short = [f'{p["page"]} ({p["apps"]} apps)' for p in self.page_log
                 if p["ok"] and p["apps"] < FULL_PAGE and p["page"] != self.pages - 1]
        if missing:
            print(f"::warning::SteamSpy pages {missing} failed or empty "
                  f"(likely cached upstream errors); saved what was available")
        if short:
            print(f"::warning::SteamSpy short pages: {', '.join(short)}")
        if records == 0:
            print("::error::SteamSpy produced zero records")
            return 1
        print(f"{records} records for the day; {self.pages_completed}/{self.pages} pages complete")
        return 0


if __name__ == "__main__":
    import os
    import sys

    async def main():
        """Run scraper with environment configuration."""
        fs = FileSystem("Data", "SteamSpyScraper")
        
        # Read config from environment with defaults
        pages = int(os.getenv('STEAMSPY_PAGES', '10'))
        page_delay = float(os.getenv('STEAMSPY_PAGE_DELAY', '15.0'))
        app_delay = float(os.getenv('STEAMSPY_APP_DELAY', '0.1'))
        
        async with SteamSpyScraper(
            fs,
            pages=pages,
            page_delay=page_delay,
            app_delay=app_delay
        ) as scraper:
            total = await scraper.scrape()
            print(f"Scraped {total} games this attempt")
            return scraper.exit_code()

    try:
        sys.exit(asyncio.run(main()))
    except Exception as e:
        print(f"✗ Scraper failed: {e}", file=sys.stderr)
        sys.exit(1)