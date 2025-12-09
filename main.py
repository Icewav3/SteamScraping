import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SteamSpy Scraper
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Setup
    """)
    return


@app.cell
def _():
    #Install Dependencies
    from src.FileSystem import FileSystem
    from src.BaseScraper import BaseScraper
    from src.SteamSpyScraper import SteamSpyScraper
    return FileSystem, SteamSpyScraper


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Run Scraper
    """)
    return


@app.cell
async def _(FileSystem, SteamSpyScraper):
    fs = FileSystem(data_dir="Data")

    # Create and run scraper
    async with SteamSpyScraper(fs, pages=10, page_delay=15, app_delay=0.1) as scraper:
        total = await scraper.scrape()
        print(f"\n✓ Complete! Scraped {total} apps")
    return


@app.cell
def _(FileSystem, SteamSpyScraper):
    import marimo as mo
    import os
    from datetime import datetime, timedelta
    from src.data_integrity import check_folder
    app = mo.App()

    @app.cell
    async def run_scraper(mo):
        fs = FileSystem(data_dir="Data")
        async with SteamSpyScraper(fs, pages=10, page_delay=15, app_delay=0.1) as scraper:
            total = await scraper.scrape()
            mo.md(f"\n✓ Complete! Scraped {total} apps")

    @app.cell
    def config_check_values():
        # Users can tweak these values in the marimo UI
        START_DATE = "2025-11-01"
        END_DATE = "2025-11-30"
        MAX_FILES = 30
        DATA_DIR = "Data"
        return START_DATE, END_DATE, MAX_FILES, DATA_DIR

    @app.cell
    def run_data_integrity(START_DATE, END_DATE, MAX_FILES, DATA_DIR, mo):
        # Validate and run checks over a date range (inclusive)
        try:
            start = datetime.fromisoformat(START_DATE).date()
            end = datetime.fromisoformat(END_DATE).date()
        except Exception as e:
            mo.md(f"Invalid date format: {e}")
            return

        if end < start:
            mo.md("END_DATE must be on or after START_DATE")
            return

        date = start
        checked = 0
        results = []
        while date <= end and checked < MAX_FILES:
            folder = os.path.join(DATA_DIR, date.isoformat())
            code = check_folder(folder)
            results.append((date.isoformat(), code))
            checked += 1
            date = date + timedelta(days=1)

        # Display result summary
        mo.md("### Data Integrity Results")
        ok = [d for d, c in results if c == 0]
        failed = [(d, c) for d, c in results if c != 0]
        mo.md(f"✔️ Passed: {len(ok)} days")
        if failed:
            for d, c in failed:
                mo.md(f"❌ {d} failed (exit code {c})")
        else:
            mo.md("All checked folders passed ✅")
        return results

    if __name__ == "__main__":
        app.run()
    return (mo,)


if __name__ == "__main__":
    app.run()
