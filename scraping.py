# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "aiohttp>=3.13.2",
#     "marimo>=0.17.0",
#     "nest-asyncio>=1.6.0",
#     "pyzmq>=27.1.0",
#     "tqdm>=4.67.1",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App()


@app.cell
def _():
    # '%pip install aiohttp nest_asyncio' command supported automatically in marimo
    # '%pip install ipywidgets' command supported automatically in marimo
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Imports
    """)
    return


@app.cell
def _():
    import os
    import json
    import asyncio
    import aiohttp
    from tqdm.notebook import tqdm
    import nest_asyncio
    from datetime import datetime
    return aiohttp, asyncio, datetime, json, nest_asyncio, os, tqdm


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Constants
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Amount of pages to scrape from steamspy (each page is ~1000 games)
    """)
    return


@app.cell
def _():
    STEAMSPY_PAGES = 10
    return (STEAMSPY_PAGES,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Setting up data folder to save to
    """)
    return


@app.cell
def _(datetime, os):
    DATA_DIR = "Data"
    TODAY_DATE = datetime.now().strftime("%Y-%m-%d")
    DAILY_DATA_DIR = os.path.join(DATA_DIR, TODAY_DATE)
    os.makedirs(DAILY_DATA_DIR, exist_ok=True)

    OUTPUT_FILE = os.path.join(DAILY_DATA_DIR, "steamspy_data.jsonl")
    PROGRESS_LOG = os.path.join(DAILY_DATA_DIR, "scraped_appids.txt")
    ERROR_LOG = os.path.join(DAILY_DATA_DIR, "steamspy_errors.log")
    META_FILE = os.path.join(DAILY_DATA_DIR, "metadata.json")
    return ERROR_LOG, META_FILE, OUTPUT_FILE, PROGRESS_LOG


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Async setup & steamspy definition
    """)
    return


@app.cell
def _(nest_asyncio):
    nest_asyncio.apply()
    BASE_URL = "https://steamspy.com/api.php"
    ALL_REQUEST_DELAY = 1  # seconds between 'all' page requests
    APPDETAILS_RATE_INTERVAL = 0.1  # seconds between appdetails requests
    return ALL_REQUEST_DELAY, APPDETAILS_RATE_INTERVAL, BASE_URL


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Async class
    """)
    return


@app.cell
def _(APPDETAILS_RATE_INTERVAL, asyncio):
    class RateLimiter:
        def __init__(self, interval):
            self.interval = interval
            self.lock = asyncio.Lock()
            self.last_called = 0

        async def __aenter__(self):
            async with self.lock:
                now = asyncio.get_event_loop().time()
                # Calculate if we need to wait
                wait_time = self.interval - (now - self.last_called)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                self.last_called = asyncio.get_event_loop().time()

        async def __aexit__(self, exc_type, exc, tb):
            pass

    # Create a global rate limiter for app details requests
    appdetails_rate_limiter = RateLimiter(APPDETAILS_RATE_INTERVAL)
    return (appdetails_rate_limiter,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Logging functions
    """)
    return


@app.cell
def _(ERROR_LOG, META_FILE, PROGRESS_LOG, json, os):
    def log_error(message):
        """Append error message to the error log file."""
        with open(ERROR_LOG, 'a', encoding='utf-8') as f:
            f.write(message + '\n')

    def save_progress(appid):
        """Append a successfully scraped appid to the progress log."""
        with open(PROGRESS_LOG, 'a', encoding='utf-8') as f:
            f.write(str(appid) + '\n')

    def load_scraped_ids():
        """Load all appids that have been scraped already."""
        if os.path.exists(PROGRESS_LOG):
            with open(PROGRESS_LOG, 'r', encoding='utf-8') as f:
                return set(int(line.strip()) for line in f if line.strip())
        return set()
    def save_metadata(metadata):
        """Save metadata to a JSON file."""
        with open(META_FILE, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=4)
    return load_scraped_ids, log_error, save_progress


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Async querying
    """)
    return


@app.cell
def _(BASE_URL, appdetails_rate_limiter, log_error):
    async def get_all_apps(session, page=0):
        """Fetch the 'all' endpoint which returns a list of apps for a given page."""
        params = {"request": "all", "page": page}
        try:
            async with session.get(BASE_URL, params=params) as response:
                if response.status != 200:
                    log_error(f"Error on all page {page}: HTTP {response.status}")
                    return {}
                return await response.json()
        except Exception as e:
            log_error(f"Error on all page {page}: {e}")
            return {}

    async def fetch_app_details(session, appid):
        """Fetch details for a single app using the rate limiter."""
        params = {"request": "appdetails", "appid": appid}

        # Wait for token before doing the request.
        async with appdetails_rate_limiter:
            try:
                async with session.get(BASE_URL, params=params) as response:
                    if response.status != 200:
                        log_error(f"App {appid}: HTTP {response.status}")
                        return None
                    data = await response.json()
                    # Filter out if the developer has hidden the data
                    if data.get("appid") == 999999:
                        return None
                    return data
            except Exception as e:
                log_error(f"App {appid}: {e}")
                return None
    return fetch_app_details, get_all_apps


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Scraping data
    """)
    return


@app.cell
def _(
    ALL_REQUEST_DELAY,
    OUTPUT_FILE,
    aiohttp,
    asyncio,
    fetch_app_details,
    get_all_apps,
    json,
    load_scraped_ids,
    save_progress,
    tqdm,
):
    async def scrape_appdetails_for_list(session, app_ids):
        """
        For each appid in app_ids (skipping already scraped ones),
        scrape app details and append data to the output file.
        Returns the count of new apps scraped.
        """
        scraped_ids = load_scraped_ids()
        new_scraped = 0

        # Open output file in append mode
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            # Use tqdm to monitor progress
            for appid in tqdm(app_ids, desc="Scraping appdetails"):
                # Skip if already processed
                if appid in scraped_ids:
                    continue
                data = await fetch_app_details(session, appid)
                if data:
                    json.dump(data, f)
                    f.write('\n')
                    save_progress(appid)
                    new_scraped += 1
        return new_scraped

    async def scrape_all(max_pages=2):
        """
        Main async function that iterates over pages of 'all' endpoints,
        gathers app ids, and calls app details scraper.
        Respects the 60-second delay between consecutive 'all' page requests only if new data was scraped.
        """
        async with aiohttp.ClientSession() as session:
            for page in range(max_pages):
                print(f"\nFetching app list from page {page}...")
                apps = await get_all_apps(session, page=page)
                if not apps:
                    print(f"Warning: No apps returned for page {page}")
                    continue

                # Extract app IDs from keys of the JSON result
                app_ids = [int(appid) for appid in apps.keys()]
                new_count = await scrape_appdetails_for_list(session, app_ids)
                print(f"Page {page} - New apps scraped: {new_count}")

                # Only wait if new data was scraped (and it's not the last page)
                if page < max_pages - 1:
                    if new_count > 0:
                        print("Waiting 60 seconds before fetching next page...")
                        await asyncio.sleep(ALL_REQUEST_DELAY)
                    else:
                        print("No new data scraped, skipping delay for next page.")
    return (scrape_all,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Scraping time
    """)
    return


@app.cell
async def _(STEAMSPY_PAGES, scrape_all):
    await scrape_all(max_pages=STEAMSPY_PAGES)
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


if __name__ == "__main__":
    app.run()
