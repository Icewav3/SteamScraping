"""Run RAWG scraper with environment configuration."""
import asyncio
import os
import sys

from src.FileSystem import FileSystem
from src.RAWGScraper import RAWGScraper


async def main():
    """Run RAWG scraper with config from environment variables."""
    api_key = os.getenv('RAWG_API_KEY')
    
    if not api_key:
        raise ValueError("RAWG_API_KEY must be set")
    
    fs = FileSystem("Data", "RAWGScraper")
    pages = int(os.getenv('RAWG_PAGES', '100'))
    
    async with RAWGScraper(fs, api_key, pages=pages) as scraper:
        total = await scraper.scrape()
        print(f"total={total}")
        return total


if __name__ == "__main__":
    try:
        total = asyncio.run(main())
        sys.exit(0 if total > 0 else 1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)