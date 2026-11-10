# src/IGDBScraper.py
"""IGDBScraper - Scrapes game data from IGDB API (Twitch/Amazon)."""
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from .BaseScraper import BaseScraper
from .FileSystem import FileSystem
from .RateLimiter import RateLimiter

# IGDB external_games source id for Steam. `external_game_source` replaced the
# deprecated `category`; both are tried, newest first.
STEAM_SOURCE = 1
LINK_SOURCE_FIELDS = ("external_game_source", "category")
# Safety cap on link pages (500 each); hitting it fails the run, never truncates.
LINKS_MAX_PAGES = 2000


class IGDBScraper(BaseScraper):
    """Scraper for IGDB API with OAuth2 and rate limiting."""
    
    def __init__(self, filesystem: FileSystem, client_id: str, client_secret: str,
                 pages: int = 100, delay: float = 0.25, 
                 suppress_output: bool = False):
        """
        Args:
            filesystem: FileSystem instance
            client_id: Twitch Client ID
            client_secret: Twitch Client Secret
            pages: Number of pages to scrape (500 games/page max)
            delay: Seconds between requests (IGDB: 4 req/sec max, so 0.25s min)
            suppress_output: Suppress print statements
        """
        super().__init__(filesystem, suppress_output)
        
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://api.igdb.com/v4"
        self.auth_url = "https://id.twitch.tv/oauth2/token"
        self.pages = pages
        self.page_size = 500  # Max allowed by IGDB
        self.rate_limiter = RateLimiter(max(delay, 0.25))  # Min 0.25s = 4 req/s
        
        self.access_token = None
        self.token_expires_at = None
        
        self.output_file = "igdb_data.jsonl"
        self.progress_file = "scraped_game_ids.txt"
        self.error_file = "igdb_errors.log"

        self.links_file = "steam_links.jsonl"

        self.base_fields = (
            "id, name, rating, rating_count, aggregated_rating, "
            "aggregated_rating_count, first_release_date, "
            "genres.name, platforms.name, involved_companies.company.name"
        )
    
    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token from Twitch."""
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            async with self.session.post(self.auth_url, params=params) as resp:
                if resp.status != 200:
                    self.log_error(f"Auth failed: HTTP {resp.status}", self.error_file)
                    return None
                
                data = await resp.json()
                self.access_token = data.get('access_token')
                expires_in = data.get('expires_in', 5184000)  # Default 60 days
                self.token_expires_at = datetime.now() + timedelta(seconds=expires_in - 3600)
                
                self._print(f"✓ Authenticated (token valid for {expires_in//86400} days)")
                return self.access_token
        
        except Exception as e:
            self.log_error(f"Auth error: {e}", self.error_file)
            return None
    
    async def _request(self, endpoint: str, body: str) -> Optional[Any]:
        """
        Make API request with error handling.
        
        Args:
            endpoint: API endpoint (e.g., "games")
            body: Request body in Apicalypse query language
        """
        token = await self._get_access_token()
        if not token:
            return None
        
        url = f"{self.base_url}/{endpoint}"
        headers = {
            'Client-ID': self.client_id,
            'Authorization': f'Bearer {token}',
            'Accept': 'application/json'
        }
        
        try:
            async with self.rate_limiter:
                async with self.session.post(url, headers=headers, data=body) as resp:
                    if resp.status == 401:  # Token expired
                        self.access_token = None
                        return await self._request(endpoint, body)  # Retry once
                    
                    if resp.status != 200:
                        text = await resp.text()
                        self.log_error(f"HTTP {resp.status} for {endpoint}: {text}", self.error_file)
                        return None
                    
                    return await resp.json()
        
        except Exception as e:
            self.log_error(f"{endpoint}: {e}", self.error_file)
            return None
    
    async def scrape(self, progress_callback=None) -> int:
        """
        Scrape IGDB games.
        
        Args:
            progress_callback: Optional callback(current, total, label)
        
        Returns:
            Number of games scraped
        """
        scraped_ids = self.load_progress(self.progress_file)
        total_scraped = 0
        fields = self.base_fields

        for page in range(self.pages):
            offset = page * self.page_size
            self._print(f"\nFetching page {page + 1}/{self.pages} (offset {offset})...")

            def build_query(f: str) -> str:
                return f"""
                    fields {f};
                    limit {self.page_size};
                    offset {offset};
                    where rating_count > 0;
                    sort rating_count desc;
                """

            games = await self._request("games", build_query(fields))

            if not games or len(games) == 0:
                self._print(f"No more results at page {page + 1}, stopping.")
                break
            
            for i, game in enumerate(games):
                if progress_callback:
                    progress_callback(i, len(games), f"Page {page + 1}")
                
                game_id = str(game.get('id'))
                if game_id in scraped_ids:
                    continue
                
                # Basic validation
                if game.get('id') and game.get('name'):
                    self.fs.append_jsonl(game, self.output_file)
                    self.save_progress(game_id, self.progress_file)
                    total_scraped += 1
            
            self._print(f"Page {page + 1} complete: {len(games)} games, {total_scraped} total scraped")
            
            # If we got fewer results than page_size, we've reached the end
            if len(games) < self.page_size:
                self._print("Reached end of available data.")
                break
        
        self.save_metadata({
            "pages_scraped": page + 1,
            "games_scraped": total_scraped,
            "client_id": self.client_id,
            "page_size": self.page_size
        })
        
        return total_scraped

    async def _links_page(self, field: str, after_id: int) -> Optional[Any]:
        return await self._request(
            "external_games",
            f"fields id, game, uid; where {field} = {STEAM_SOURCE} & id > {after_id}; "
            f"sort id asc; limit {self.page_size};")

    async def scrape_steam_links(self) -> int:
        """Snapshot every IGDB game <-> Steam appid link.

        Covers all of IGDB, not just the rated games scrape() collects.
        igdb_id is stable, so the newest snapshot links the whole igdb
        history to Steam. Pages by id cursor and rewrites the file whole,
        so retries never duplicate. Returns the link count, 0 on failure.
        """
        field, batch = None, None
        for candidate in LINK_SOURCE_FIELDS:
            batch = await self._links_page(candidate, 0)
            if batch:
                field = candidate
                break
            self.log_error(f"external_games on '{candidate}' returned nothing",
                           self.error_file)
        if field is None:
            return 0

        links, pages = [], 1
        while batch:
            for ext in batch:
                uid, game = str(ext.get("uid", "")), ext.get("game")
                if uid.isdigit() and isinstance(game, int):
                    links.append({"igdb_id": game, "steam_appid": int(uid)})
            if len(batch) < self.page_size:
                break
            if pages >= LINKS_MAX_PAGES:
                self.log_error("external_games hit LINKS_MAX_PAGES", self.error_file)
                return 0
            batch = await self._links_page(field, batch[-1]["id"])
            pages += 1
            if batch is None:
                self.log_error(f"external_games failed on page {pages}", self.error_file)
                return 0

        self.fs.write_jsonl(links, self.links_file)
        self._print(f"Steam links: {len(links)} via '{field}' ({pages} pages)")
        return len(links)


if __name__ == "__main__":
    import os
    import sys
    
    async def main():
        """Run scraper with environment configuration."""
        client_id = os.getenv('IGDB_CLIENT_ID')
        client_secret = os.getenv('IGDB_CLIENT_SECRET')
        
        if not client_id or not client_secret:
            raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
        
        fs = FileSystem("Data", "IGDBScraper")
        pages = int(os.getenv('IGDB_PAGES', '100'))
        
        async with IGDBScraper(fs, client_id, client_secret, pages=pages) as scraper:
            total = await scraper.scrape()
            links = await scraper.scrape_steam_links()
            games_today = len(scraper.load_progress(scraper.progress_file))
            print(f"total={total} games_today={games_today} steam_links={links}")
            # Judge the day, not the attempt: a retry that only redoes the
            # links scrapes 0 new games and is still a success.
            return games_today > 0 and links > 0
    
    try:
        sys.exit(0 if asyncio.run(main()) else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)