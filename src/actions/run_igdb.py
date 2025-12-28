#!/usr/bin/env python3
"""Run IGDB scraper with environment configuration."""
import asyncio
import os
import sys

from src.FileSystem import FileSystem
from src.IGDBScraper import IGDBScraper


async def main():
    """Run IGDB scraper with config from environment variables."""
    client_id = os.getenv('IGDB_CLIENT_ID')
    client_secret = os.getenv('IGDB_CLIENT_SECRET')
    
    if not client_id or not client_secret:
        raise ValueError("IGDB_CLIENT_ID and IGDB_CLIENT_SECRET must be set")
    
    fs = FileSystem("Data", "IGDBScraper")
    pages = int(os.getenv('IGDB_PAGES', '50'))
    
    async with IGDBScraper(
        fs,
        client_id,
        client_secret,
        pages=pages
    ) as scraper:
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