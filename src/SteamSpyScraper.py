"""SteamSpyScraper - Scrapes game data from SteamSpy API."""
import asyncio
from typing import Dict, Any, Optional
from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter


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
    
    async def _request(self, request_type: str, **kwargs) -> Optional[Dict[str, Any]]:
        """Make API request."""
        params = {"request": request_type, **kwargs}
        
        try:
            async with self.session.get(self.base_url, params=params) as resp:
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
            apps = await self._request("all", page=page)
            
            if not apps:
                self._print(f"No apps on page {page}, stopping.")
                break
            
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
            
            self._print(f"Page {page}: scraped {len(app_ids)} apps")
            if self.page_delay > 0:
                await asyncio.sleep(self.page_delay)
        
        self.save_metadata({"pages_scraped": page + 1, "apps_scraped": total_scraped})
        return total_scraped
    
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
            print(f"✓ Scraped {total} games")
            return total

    try:
        total = asyncio.run(main())
        sys.exit(0 if total > 0 else 1)
    except Exception as e:
        print(f"✗ Scraper failed: {e}", file=sys.stderr)
        sys.exit(1)