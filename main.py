import marimo

__generated_with = "0.18.3"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # 🎮 SteamSpy Scraper Dashboard
    
    Welcome to the SteamSpy data collection and analysis dashboard.
    
    Use the navigation menu below to access different features:
    - **Scraper** - Collect game data from SteamSpy
    - **Validator** - Check data integrity
    - **Visualizer** - Analyze trends and patterns
    """)
    return


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell
def _(mo):
    # Navigation menu
    nav = mo.ui.nav_menu(
        {
            "🔧 Scraper": "scraper",
            "✅ Validator": "validator", 
            "📊 Visualizer": "visualizer",
        },
        orientation="vertical",
    )
    return nav


@app.cell
def _(mo, nav):
    mo.md("""
    ## Quick Links
    
    **To get started:**
    
    1. Use the **Scraper** to download game data from SteamSpy
    2. Check with **Validator** that your data is intact
    3. Explore trends in **Visualizer**
    
    ---
    
    ## Running Individual Modules
    
    You can also run each module independently for more focused workflows:
    
    ```powershell
    # Scraper only
    uv run marimo ui/scraper.py
    
    # Validator only  
    uv run marimo ui/validator.py
    
    # Visualizer only
    uv run marimo ui/visualization.py
    ```
    
    ## CLI Tools
    
    Validate data from the command line:
    
    ```powershell
    python validate_data.py --path Data/2025-12-09
    ```
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    
    ## Architecture
    
    This dashboard is built on a **Model-View-Controller (MVC)** architecture:
    
    - **Engine**: Pure Python modules in `src/` (zero marimo dependency)
    - **UI**: Marimo apps for interactive control
    - **Data**: Local file storage in `Data/` directory
    
    Learn more: see [README.md](README.md) and [MIGRATION_GUIDE.md](MIGRATION_GUIDE.md)
    """)
    return


if __name__ == "__main__":
    app.run()
