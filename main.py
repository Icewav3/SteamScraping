# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "aiohttp>=3.13.2",
#     "marimo>=0.17.0",
#     "pyzmq>=27.1.0",
#     "tqdm>=4.67.1",
# ]
# ///

import marimo

__generated_with = "0.18.4"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # SteamSpy Scraper
    """)
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


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
def _(mo):
    user_pages = mo.ui.number(start=1, stop=100, step=1, value=10, label="Pages")
    user_page_delay = mo.ui.number(start=0.0, stop=15.0, step=0.1, value=5.0, label="Page Delay (s)")
    user_app_delay = mo.ui.number(start=0.0, stop=10.0, step=0.1, value=0.1, label="App Delay (s)")

    mo.vstack([user_pages, user_page_delay, user_app_delay])
    return user_app_delay, user_page_delay, user_pages


@app.cell
async def _(
    FileSystem,
    SteamSpyScraper,
    mo,
    user_app_delay,
    user_page_delay,
    user_pages,
):
    fs = FileSystem(data_dir="Data")
    SteamspyEnteriesPerPage = 1000
    TotalEntriesToScrape = user_pages.value * SteamspyEnteriesPerPage
    with mo.status.progress_bar(total=10*SteamspyEnteriesPerPage, title="Scraping SteamSpy") as bar:
        def progress_callback(current, total, label):
            """Update progress bar subtitle."""
            bar.update(subtitle=f"{label}: {1+current}/{total}")

        async with SteamSpyScraper(fs, pages=user_pages.value, page_delay=user_page_delay.value, app_delay=user_app_delay.value, suppress_output=True) as scraper:
            total = await scraper.scrape(progress_callback=progress_callback)

    print(f"✓ Complete! Scraped {total} apps")
    return


if __name__ == "__main__":
    app.run()
