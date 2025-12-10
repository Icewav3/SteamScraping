# Game Industry Market Analysis

Quantify and visualize the Steam games market by scraping and analyzing SteamSpy data.

## Quick Start

### Setup
```powershell
uv sync
uv run marimo main.py
```

---

## Architecture

This project follows **Model-View-Controller (MVC)** principles:

### Engine (Model)
- **`src/core/`** - Abstract base classes and utilities (BaseScraper, RateLimiter)
- **`src/scrapers/`** - Concrete scraper implementations (SteamSpyScraper)
- **`src/storage/`** - File I/O operations (FileSystem)
- **`src/validation/`** - Data integrity validation (DataValidator)
- **`src/models/`** - Structured data types (ScrapingResult, ValidationResult)

Pure Python modules with **zero marimo dependency** for maximum reusability and testability.

### UI (View/Controller)
- **`main.py`** - Dashboard entry point
- **`ui/scraper.py`** - Configure and run scraper
- **`ui/validator.py`** - Validate scraped data
- **`ui/visualization.py`** - Analyze and visualize data

Modular marimo apps with reactive UI controls.

---

## Usage

### Running the Dashboard
```powershell
uv run marimo main.py
```

Then access individual modules from the dashboard or run directly:
```powershell
uv run marimo ui/scraper.py
uv run marimo ui/validator.py
uv run marimo ui/visualization.py
```

### Validating Data (CLI)
```powershell
python validate_data.py --path Data/2025-12-09
python validate_data.py -p Data/2025-12-09
```

---

## Project Structure

```
project-root/
├── main.py                   # Dashboard entry point
├── validate_data.py          # CLI data validator
├── pyproject.toml            # Project dependencies
│
├── src/                      # Core engine (pure Python)
│   ├── __init__.py          # Main exports
│   ├── core/                # Base classes & utilities
│   │   ├── scraper.py       # BaseScraper abstract class
│   │   └── rate_limiter.py  # RateLimiter for API requests
│   ├── scrapers/            # Concrete scrapers
│   │   └── steamspy.py      # SteamSpy API scraper
│   ├── storage/             # File operations
│   │   └── filesystem.py    # FileSystem manager
│   ├── validation/          # Data validation
│   │   └── integrity.py     # DataValidator
│   └── models/              # Data types
│       └── types.py         # ScrapingResult, ValidationResult
│
├── ui/                      # Marimo UI modules
│   ├── scraper.py          # Scraper control interface
│   ├── validator.py        # Data validation interface
│   └── visualization.py    # Data analysis & visualization
│
├── Data/                    # Output data (auto-created)
│   └── YYYY-MM-DD/          # One folder per scrape date
│       ├── steamspy_data.jsonl     # Main dataset (JSONL format)
│       ├── scraped_appids.txt      # List of app IDs scraped
│       ├── metadata.json           # Scraping metadata
│       └── steamspy_errors.log     # Error log (if any)
│
└── _archived/              # Old notebooks and deprecated files
```

---

## Data Structure

Each scraping session creates a dated folder with:

- **`steamspy_data.jsonl`** - Raw game data (one JSON object per line)
- **`scraped_appids.txt`** - Unique app IDs (one per line)
- **`metadata.json`** - Scraping session metadata

---

## Development

### Add a New Scraper
1. Create a file in `src/scrapers/` and extend `BaseScraper`
2. Implement `async def scrape() -> ScrapingResult`
3. Export in `src/scrapers/__init__.py`

### Extend Validation
Modify `src/validation/integrity.py` to add custom checks.

### Modify UI
Edit files in `ui/` folder and import from `src` as needed.

---

## TODO

### Medium Priority
- Add comparative time-series analysis to visualization module
- Create data export formats (CSV, Parquet)

### Long term goals
- Integrate additional data sources (Steam Store API, ProtonDB, etc.)
- Implement asynchronous multi-source collection
- Add database backend for historical analysis
