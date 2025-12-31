# src/RAWGScraper.py
"""RAWGScraper - Scrapes game data from RAWG.io API."""
import asyncio
from typing import Optional, Dict, Any
from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter


class RAWGScraper(BaseScraper):
    """Scraper for RAWG.io API with rate limiting."""
    
    def __init__(self, filesystem: FileSystem, api_key: str,
                 pages: int = 100, delay: float = 1.0, 
                 suppress_output: bool = False):
        """
        Args:
            filesystem: FileSystem instance
            api_key: RAWG API key
            pages: Number of pages to scrape (40 games/page)
            delay: Seconds between requests (RAWG: max 1 req/sec)
            suppress_output: Suppress print statements
        """
        super().__init__(filesystem, suppress_output)
        
        self.api_key = api_key
        self.base_url = "https://api.rawg.io/api"
        self.pages = pages
        self.rate_limiter = RateLimiter(delay)
        
        self.output_file = "rawg_data.jsonl"
        self.progress_file = "scraped_game_ids.txt"
        self.error_file = "rawg_errors.log"
    
    async def _request(self, endpoint: str, **params) -> Optional[Dict[str, Any]]:
        """Make API request with error handling."""
        params['key'] = self.api_key
        url = f"{self.base_url}/{endpoint}"
        
        try:
            async with self.rate_limiter:
                async with self.session.get(url, params=params) as resp:
                    if resp.status != 200:
                        self.log_error(f"HTTP {resp.status}: {endpoint}", self.error_file)
                        return None
                    return await resp.json()
        except Exception as e:
            self.log_error(f"{endpoint}: {e}", self.error_file)
            return None
    
    async def scrape(self, progress_callback=None) -> int:
        """
        Scrape RAWG games.
        
        Args:
            progress_callback: Optional callback(current, total, label)
        
        Returns:
            Number of games scraped
        """
        scraped_ids = self.load_progress(self.progress_file)
        total_scraped = 0
        
        for page in range(1, self.pages + 1):
            self._print(f"\nFetching page {page}/{self.pages}...")
            
            data = await self._request("games", page=page, page_size=40)
            if not data or 'results' not in data:
                self._print(f"No results on page {page}, stopping.")
                break
            
            games = data['results']
            for i, game in enumerate(games):
                if progress_callback:
                    progress_callback(i, len(games), f"Page {page}")
                
                game_id = str(game.get('id'))
                if game_id in scraped_ids:
                    continue
                
                # Get detailed info
                details = await self._request(f"games/{game_id}")
                if details:
                    # Basic validation
                    if details.get('id') and details.get('name'):
                        self.fs.append_jsonl(details, self.output_file)
                        self.save_progress(game_id, self.progress_file)
                        total_scraped += 1
            
            self._print(f"Page {page} complete: {len(games)} games")
        
        self.save_metadata({
            "pages_scraped": page,
            "games_scraped": total_scraped,
            "api_key_hash": hash(self.api_key)  # For debugging key issues
        })
        
        return total_scraped
    
if __name__ == "__main__":
    import os
    import sys
    
    async def main():
        """Run scraper with environment configuration."""
        api_key = os.getenv('RAWG_API_KEY')
        
        if not api_key:
            raise ValueError("RAWG_API_KEY must be set")
        
        fs = FileSystem("Data", "RAWGScraper")
        pages = int(os.getenv('RAWG_PAGES', '100'))
        
        async with RAWGScraper(fs, api_key, pages=pages) as scraper:
            total = await scraper.scrape()
            print(f"total={total}")
            return total
    
    try:
        total = asyncio.run(main())
        sys.exit(0 if total > 0 else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)