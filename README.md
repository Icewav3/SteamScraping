# This is a ongoing project that is dedicated to attempting to quantify and visualize the market potential



## TODO (ENSURE THIS IS KEPT UP TO DATE)

- meta data json implementation
    - see details in scraping.ipynb
    - allow for (not perfect) metadata generation of old scrapes as best as possible
- abstract scraper functionality to allow for other sources beyond steamspy
    - create .py files to clean up jupyter notebook and move into seperate folder
    - add a jupyter notebook file called main.ipynb that handles running all scraping tasks
- create new visualization notebook to allow for comparitive analysis from data over a time period in Data folder
- move all visualzation code to a seperate folder, abstract what is possible to keep code clean
- create requirements.txt file for easy package installation
- create setup.py file for easy installation of package
- update project structure in readme to reflect new structure after abstraction



# Project structure:
project-root/
├── Data/                       # This folder is created when the script runs
│   └── YYYY-MM-DD/             # Data from a specific scrape/run date
│       ├── daily_metadata.json # Logged Metadata from scrape
│       ├── scraped_appids.txt  # List of items scraped
│       └── steamspy_data.jsonl # The main dataset (JSON Lines format)
└── <script_or_notebook>        # The file that creates the 'Data' folder

