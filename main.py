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
async def _(FileSystem, SteamSpyScraper):
    fs = FileSystem(data_dir="Data")

    # Create and run scraper
    async with SteamSpyScraper(fs, pages=10, page_delay=15, app_delay=0.1) as scraper:
        total = await scraper.scrape()
        print(f"\n✓ Complete! Scraped {total} apps")
    return


if __name__ == "__main__":
    app.run()
