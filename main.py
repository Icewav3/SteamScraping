# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "aiohttp>=3.13.2",
#     "beautifulsoup4>=4.12.0",
#     "duckdb>=1.5.0",
#     "marimo>=0.17.0",
#     "pyarrow>=24.0.0",
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
    from src.SteamSpyHTMLScraper import SteamSpyHTMLScraper
    from src.SteamSpyScraper import SteamSpyScraper
    return FileSystem, SteamSpyScraper, SteamSpyHTMLScraper


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

    print(f"Scraped {total} Steam apps")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Run HTML Fallback Scraper
    Use this when the SteamSpy API is down (`Connection failed: Too many connections`).
    Scrapes the steamspy.com homepage directly — returns ~200 apps instead of the full dataset
    but preserves continuity. Automatically attempts appdetails enrichment if the API recovers.
    """)
    return


@app.cell
def _(mo):
    user_html_page_delay = mo.ui.number(start=0.0, stop=15.0, step=0.1, value=1.0, label="Page Delay (s)")
    user_html_app_delay = mo.ui.number(start=0.0, stop=10.0, step=0.1, value=0.1, label="App Delay (s)")
    user_html_try_api = mo.ui.checkbox(value=True, label="Try appdetails enrichment if API recovers")

    mo.vstack([user_html_page_delay, user_html_app_delay, user_html_try_api])
    return user_html_app_delay, user_html_page_delay, user_html_try_api


@app.cell
async def _(
    FileSystem,
    SteamSpyHTMLScraper,
    mo,
    user_html_app_delay,
    user_html_page_delay,
    user_html_try_api,
):
    fs_html = FileSystem("Data", "SteamSpyScraper")  # same output dir as normal scraper

    with mo.status.progress_bar(total=200) as bar_html:
        def progress_callback_html(current, total, label):
            bar_html.update(subtitle=f"{label}: {current+1}/{total}")

        async with SteamSpyHTMLScraper(
            fs_html,
            page_delay=user_html_page_delay.value,
            app_delay=user_html_app_delay.value,
            suppress_output=True,
            try_api_fallback=user_html_try_api.value,
        ) as _scraper:
            _total = await _scraper.scrape(progress_callback=progress_callback_html)

    print(f"HTML fallback scraped {_total} Steam apps")
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Sync History & Build Warehouse
    Mirror all daily snapshots from GitHub releases into `Data/`, then ingest them
    into the queryable Parquet warehouse. Both steps are incremental and safe to re-run.
    See `DATA.md` for schemas and caveats.
    """)
    return


@app.cell
def _(mo):
    run_sync = mo.ui.run_button(label="Sync from GitHub releases")
    run_build = mo.ui.run_button(label="Build warehouse")
    mo.hstack([run_sync, run_build], justify="start")
    return run_build, run_sync


@app.cell
async def _(mo, run_sync):
    mo.stop(not run_sync.value, mo.md("*Click to download missing snapshot days.*"))

    from src.ReleaseSync import ReleaseSync

    with mo.status.spinner(title="Syncing release assets...") as _sp:
        def _sync_progress(current, total, label):
            _sp.update(subtitle=f"{label}: {current + 1}/{total}")

        _stats = await ReleaseSync().sync(progress_callback=_sync_progress)

    mo.md(f"✓ downloaded **{_stats.downloaded}** files, {_stats.skipped} already up to date")
    return


@app.cell
def _(mo, run_build):
    mo.stop(not run_build.value, mo.md("*Click to ingest synced days into Parquet.*"))

    from src.Warehouse import Warehouse

    _wh = Warehouse()
    with mo.status.spinner(title="Ingesting snapshots...") as _sp_b:
        def _build_progress(current, total, label):
            _sp_b.update(subtitle=f"{label}: {current + 1}/{total}")

        _result = _wh.build(progress_callback=_build_progress)

    mo.vstack([
        mo.md(f"✓ ingested **{len(_result['ingested'])}** days, "
              f"changes for {len(_result['changes'])} day-pairs"
              + (f" — **FAILED: {_result['failed']}**" if _result['failed'] else "")),
        mo.md(f"```\n{_wh.status()}\n```"),
    ])
    return


if __name__ == "__main__":
    app.run()