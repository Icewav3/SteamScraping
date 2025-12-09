# Game Industry Market Analysis

This is a ongoing project that is dedicated to attempting to quantify and visualize the market potential

---

```ps
uv run marimo
```

---

## TODO (keep me updated!)

### High Priority
- finish marimo migration by updating `main.py` and `src/*` to utilize built-in marimo functions instead of relying on old methods (IN PROGRESS)
    - currently marimo does not display the progress bar in the rendered marimo file in browser — fixed by adding marimo-aware progress bar in `BaseScraper.progress_bar` so scrapers will prefer marimo's progress APIs
    - check documentation before release to ensure following BEST PRACTICES FOR CLEAN CODE
    - once complete remove un-used dependencies to keep UV clean

### Medium Priority
- create data integrity checking script to ensure data was collected properly during a scrape - needs to be strict (DONE)

New: A data integrity checker is available at `src/data_integrity.py`. Run via:

```powershell
; python -m src.data_integrity --path Data/2025-11-11
```

The checker validates presence of files, ensures `steamspy_data.jsonl` is valid JSONL with an `appid` key per line, ensures `scraped_appids.txt` contains unique integers, and verifies a simple metadata structure.
- create new visualization marimo file to allow for comparitive analysis from data over a time period in Data folder

### Low Priority:
- Update readme with a table of contents as well as setup instructions

### Long term goals:
- look online to find other potential data sources to collect from
    - ensure collection is asynchronus (all run at once)

-----


* OUT OF DATE
# Project structure:
project-root/
├── Data/                       # This folder is created when the script runs
│   └── YYYY-MM-DD/             # Data from a specific scrape/run date
│       ├── daily_metadata.json # Logged Metadata from scrape
│       ├── scraped_appids.txt  # List of items scraped
│       └── steamspy_data.jsonl # The main dataset (JSON Lines format)
└── <script_or_notebook>        # The file that creates the 'Data' folder

