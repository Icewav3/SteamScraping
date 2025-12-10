"""SteamSpy API scraper."""

from typing import Dict, Any, Optional
from datetime import datetime

from ..core import BaseScraper, RateLimiter
from ..storage import FileSystem
from ..models import ScrapingResult


class SteamSpyScraper(BaseScraper):
    """Scraper for SteamSpy API."""

    def __init__(
        self,
        filesystem: FileSystem,
        pages: int = 10,
        page_delay: float = 60.0,
        app_delay: float = 0.1,
    ):
        """
        Initialize SteamSpy scraper.

        Args:
            filesystem: FileSystem for I/O operations.
            pages: Number of pages to scrape (~1000 apps each).
            page_delay: Seconds to wait between page requests.
            app_delay: Seconds to wait between app detail requests.
        """
        super().__init__(filesystem)

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
            page: Page number to fetch.

        Returns:
            Dictionary of app IDs to basic info.
        """
        params = {"request": "all", "page": page}
        try:
            async with self.session.get(self.base_url, params=params) as response:
                if response.status != 200:
                    self.log_error(
                        f"Page {page}: HTTP {response.status}", self.error_file
                    )
                    return {}
                return await response.json()
        except Exception as e:
            self.log_error(f"Page {page}: {e}", self.error_file)
            return {}

    async def _fetch_app_details(self, appid: int) -> Optional[Dict[str, Any]]:
        """
        Fetch details for a single app with rate limiting.

        Args:
            appid: Steam app ID.

        Returns:
            App details or None if failed/hidden.
        """
        params = {"request": "appdetails", "appid": appid}

        async with self.rate_limiter:
            try:
                async with self.session.get(self.base_url, params=params) as response:
                    if response.status != 200:
                        self.log_error(
                            f"App {appid}: HTTP {response.status}", self.error_file
                        )
                        return None

                    data = await response.json()

                    # Filter out hidden data (developer privacy setting)
                    if data.get("appid") == 999999:
                        return None

                    return data
            except Exception as e:
                self.log_error(f"App {appid}: {e}", self.error_file)
                return None

    async def scrape(self) -> ScrapingResult:
        """
        Scrape SteamSpy data for configured number of pages.

        Returns:
            ScrapingResult with details about the scraping run.
        """
        total_scraped = 0
        new_apps = 0
        errors = []
        scraped_ids = self.load_progress(self.progress_file)

        try:
            for page in range(self.pages):
                print(f"\nFetching app list from page {page}...")
                apps = await self._get_all_apps(page)

                if not apps:
                    msg = f"No apps returned for page {page}"
                    print(f"Warning: {msg}")
                    errors.append(msg)
                    continue

                # Get app IDs from the response
                app_ids = [int(appid) for appid in apps.keys()]
                page_new_count = 0

                # Scrape details for each app
                for appid in app_ids:
                    # Skip if already scraped
                    if str(appid) in scraped_ids:
                        continue

                    data = await self._fetch_app_details(appid)
                    if data:
                        self.fs.append_jsonl(data, self.output_file)
                        self.save_progress(str(appid), self.progress_file)
                        page_new_count += 1
                        new_apps += 1

                print(f"Page {page} - New apps scraped: {page_new_count}")
                total_scraped += len(app_ids)

                # Wait between pages (except last page)
                if page < self.pages - 1 and page_new_count > 0:
                    print(f"Waiting {self.page_delay} seconds...")
                    import asyncio

                    await asyncio.sleep(self.page_delay)

        except Exception as e:
            errors.append(str(e))
            self.log_error(f"Fatal error during scraping: {e}", self.error_file)

        # Save metadata
        end_time = datetime.now()
        metadata = {
            "start_time": self.start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "pages_scraped": self.pages,
            "apps_scraped": new_apps,
            "total_processed": total_scraped,
        }
        self.fs.save_json(metadata, self.metadata_file)

        return ScrapingResult(
            total_scraped=new_apps,
            new_apps=new_apps,
            errors=errors,
            start_time=self.start_time,
            end_time=end_time,
            metadata=metadata,
        )
