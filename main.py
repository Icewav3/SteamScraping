# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "aiohttp>=3.13.2",
#     "marimo>=0.17.0",
#     "pandera==0.27.1",
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
    from src.FileSystem import FileSystem
    from src.SteamSpyScraper import SteamSpyScraper
    from src.RAWGScraper import RAWGScraper
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
    user_page_delay = mo.ui.number(start=0.0, stop=15.0, step=0.1, value=0.0, label="Page Delay (s)")
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
    fs_steamspy = FileSystem("Data", "SteamSpyScraper")

    with mo.status.progress_bar(total=user_pages.value * 1000) as bar:
        def progress_callback(current, total, label):
            bar.update(subtitle=f"{label}: {current+1}/{total}")

        async with SteamSpyScraper(
            fs_steamspy, 
            pages=user_pages.value,
            page_delay=user_page_delay.value,
            app_delay=user_app_delay.value,
            suppress_output=True
        ) as scraper:
            total = await scraper.scrape(progress_callback=progress_callback)

    print(f"✓ Scraped {total} Steam apps")
    return


if __name__ == "__main__":
    app.run()
