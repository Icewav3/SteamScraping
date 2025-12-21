"""
SteamSpyScraper - Scrapes game data from SteamSpy API.
"""
import asyncio
from typing import Dict, Any, Optional

from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter


class SteamSpyScraper(BaseScraper):
    """Scraper for SteamSpy API."""
    
    def __init__(self, filesystem: FileSystem, 
                 pages: int = 10,
                 page_delay: float = 5.0,
                 app_delay: float = 0.1,
                 suppress_output: bool = False):
        """
        Initialize SteamSpy scraper.
        
        Args:
            filesystem: FileSystem for I/O operations
            pages: Number of pages to scrape (~1000 apps each)
            page_delay: Seconds to wait between page requests
            app_delay: Seconds to wait between app detail requests
            suppress_output: If True, suppress print statements
        """
        super().__init__(filesystem, suppress_output=suppress_output)
        
        self.base_url = "https://steamspy.com/api.php"
        self.pages = pages
        self.page_delay = page_delay
        self.rate_limiter = RateLimiter(app_delay)
        
        # File names
        self.output_file = "steamspy_data.jsonl"
        self.progress_file = "scraped_appids.txt"
        self.error_file = "steamspy_errors.log"
        self.metadata_file = "metadata.json"
    
    async def _get_all_apps(self, page: int) -> Dict[str, Any]:
        """
        Fetch list of apps for a given page.
        
        Args:
            page: Page number to fetch
            
        Returns:
            Dictionary of app IDs to basic info
        """
        params = {"request": "all", "page": page}
        try:
            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    self.log_error(f"Page {page}: HTTP {response.status}", self.error_file)
                    return {}
                return await response.json()
        except Exception as e:
            self.log_error(f"Page {page}: {e}", self.error_file)
            return {}
    
    async def _fetch_app_details(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a single app with rate limiting.
        
        Args:
            appid: Steam app ID
            
        Returns:
            App details or None if failed/hidden
        """
        params = {"request": "appdetails", "appid": appid}
        
        async with self.rate_limiter:
            try:
                async with self.session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        self.log_error(f"App {appid}: HTTP {response.status}", self.error_file)
                        return None
                    
                    data = await response.json()
                    
                    # Filter out hidden data (developer privacy setting)
                    if data.get("appid") == 999999:
                        return None
                    
                    return data
            except Exception as e:
                self.log_error(f"App {appid}: {e}", self.error_file)
                return None
    
    async def _process_app(self, appid: int, scraped_ids: set) -> Optional[Dict[str, Any]]:
        """
        Process a single app: fetch details and save if new.
        
        Args:
            appid: Steam app ID
            scraped_ids: Set of already scraped app IDs
            
        Returns:
            App data if successfully scraped, None otherwise
        """
        # Skip if already scraped
        if str(appid) in scraped_ids:
            return None
        
        data = await self._fetch_app_details(appid)
        if data:
            self.fs.append_jsonl(data, self.output_file)
            self.save_progress(str(appid), self.progress_file)
            return data
        
        return None
    
    async def scrape(self, progress_callback=None) -> int:
        """
        Scrape SteamSpy data for configured number of pages.
        
        Args:
            progress_callback: Optional callback(current, total, desc) for progress updates
        
        Returns:
            Total number of apps scraped
        """
        total_scraped = 0
        scraped_ids = self.load_progress(self.progress_file)
        
        for page in range(self.pages):
            self._print(f"\nFetching app list from page {page}...")
            apps = await self._get_all_apps(page)
            
            if not apps:
                self._print(f"Warning: No apps returned for page {page}")
                continue
            
            # Get app IDs from the response
            app_ids = [int(appid) for appid in apps.keys()]
            
            # Process all apps in this page
            async def process_single_app(appid):
                return await self._process_app(appid, scraped_ids)
            
            new_count = await self.process_items_in_batches(
                items=app_ids,
                process_func=process_single_app,
                batch_label=f"Page {page}",
                progress_callback=progress_callback,
                batch_delay=self.page_delay if page < self.pages - 1 else None
            )
            
            self._print(f"Page {page} - New apps scraped: {new_count}")
            total_scraped += new_count
            
            # Print delay message if there's a next page
            if page < self.pages - 1 and new_count > 0:
                self._print(f"Waiting {self.page_delay} seconds...")
        
        # Save metadata
        metadata = {
            "start_time": self.start_time.isoformat(),
            "end_time": asyncio.get_event_loop().time(),
            "pages_scraped": self.pages,
            "apps_scraped": total_scraped
        }
        self.fs.save_json(metadata, self.metadata_file)
        
        return total_scraped