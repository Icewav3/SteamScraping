# This is a ongoing project that is dedicated to attempting to quantify and visualize the market potential

# RULES
 Files must be readable and well documented.
 Code needs to be short and sweet. Abstract when nesessary.
 Visualizations need to be clear and concise. Avoid clutter.



## TODO (ENSURE THIS IS KEPT UP TO DATE)

- meta data json implementation
    - see details in scraping.ipynb
    - allow for (not perfect) metadata generation of old scrapes as best as possible
- abstract scraper functionality to allow for other sources beyond steamspy
    - base scraper class should be abstract in order to work with many sources
    - create .py files to clean up jupyter notebook and move into seperate folder
    - add a jupyter notebook file called main.ipynb that handles running all scraping tasks
- create new visualization notebook to allow for comparitive analysis from data over a time period in Data folder
- create requirements.txt file for easy package installation
- create setup.py file for easy installation of package



# Project structure:
project-root/
├── Data/                       # This folder is created when the script runs
│   └── YYYY-MM-DD/             # Data from a specific scrape/run date
│       ├── daily_metadata.json # Logged Metadata from scrape
│       ├── scraped_appids.txt  # List of items scraped
│       └── steamspy_data.jsonl # The main dataset (JSON Lines format)
└── src/                        # scripts folder
    ├── FileReadWrite.py        # filo io operations
    ├── BaseScraper.py          # abstract scraper class (has metadata tracking)
    ├── SteamSpyScraper.py      # steamspy scraper class (extends BaseScraper)
    ├── main.ipynb              # Jupyter notebook for scraping data (should be tiny)
    └── visualizations.ipynb    # Jupyter notebook for visualizing the scraped data
└── README.md                   # Project documentation (this file)

