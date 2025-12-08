# Game Industry Market Analysis

This is a ongoing project that is dedicated to attempting to quantify and visualize the market potential

---

## TODO (keep me updated!)

### High Priority
- finish marimo migration by updating main.py to utilize built in marimo functions instead of relying on old methods
    - currently marimo does not display the progress bar in the rendered marimo file in browser.
    - check documentation before this to ensure following BEST PRACTICES FOR CLEAN CODE
    - once complete remove un-used dependancies to keep UV clean

### Medium Priority
- create data integrity checking script to ensure data was collected properly during a scrape - needs to be strict
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

