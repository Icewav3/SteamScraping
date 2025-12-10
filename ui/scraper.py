import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🚀 Scraper Control

    Configure and run the SteamSpy scraper to download game data.
    """)
    return


@app.cell
def _():
    import marimo as mo
    from src.storage import FileSystem
    from src.scrapers import SteamSpyScraper
    return FileSystem, SteamSpyScraper, mo


@app.cell
def _(mo):
    mo.md("""
    ## Configuration
    """)
    return


@app.cell
def _(mo):
    # Create sliders for configuration
    pages = mo.ui.slider(1, 100, value=10, label="Number of pages to scrape (~1000 games/page)")
    page_delay = mo.ui.slider(0, 300, value=60, step=5, label="Delay between pages (seconds)")
    app_delay = mo.ui.slider(0.01, 1, value=0.1, step=0.01, label="Delay between app requests (seconds)")

    return app_delay, page_delay, pages


@app.cell
def _(app_delay, mo, page_delay, pages):
    mo.md(f"""
    **Current Settings:**
    - Pages: {pages.value}
    - Page delay: {page_delay.value}s
    - App delay: {app_delay.value}s
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ## Run Scraper
    """)
    return


@app.cell
def _(mo):
    run_button = mo.ui.run_button(label="🚀 Start Scraping", kind="success")
    return (run_button,)


@app.cell
async def _(
    FileSystem,
    SteamSpyScraper,
    app_delay,
    mo,
    page_delay,
    pages,
    run_button,
):
    result_display = None

    if run_button.clicked:
        try:
            fs = FileSystem(data_dir="Data")

            async with SteamSpyScraper(
                fs,
                pages=pages.value,
                page_delay=page_delay.value,
                app_delay=app_delay.value,
            ) as scraper:
                with mo.status.spinner(title="Scraping data...", show_time=True):
                    result = await scraper.scrape()

            result_display = mo.md(f"""
            ## ✅ Scraping Complete!

            {result}

            **Data saved to:** `{fs.daily_dir}`
            """)
        except Exception as e:
            result_display = mo.md(f"""
            ## ❌ Error

            {str(e)}

            Check the console for more details.
            """)

    return


if __name__ == "__main__":
    app.run()
