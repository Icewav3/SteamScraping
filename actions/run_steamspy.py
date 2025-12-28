#!/usr/bin/env python3
"""Run SteamSpy scraper with environment configuration.

GitHub Actions runner script.
"""
import asyncio
import os
import sys

from src.FileSystem import FileSystem
from src.SteamSpyScraper import SteamSpyScraper


async def main():
    """Run SteamSpy scraper with config from environment variables."""
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


if __name__ == "__main__":
    try:
        total = asyncio.run(main())
        # Exit with error if nothing was scraped
        sys.exit(0 if total > 0 else 1)
    except Exception as e:
        print(f"✗ Scraper failed: {e}", file=sys.stderr)
        sys.exit(1)