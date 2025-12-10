# Migration Guide: Old to New Architecture

This document explains the changes made during the refactoring and how to use the new architecture.

## What Changed

### Code Structure

**Old:**
```
├── main.py (with mixed logic)
├── scraping.py (messy notebook)
├── visualization.py (incomplete)
├── visualization_multi.py (non-functional)
├── src/
│   ├── BaseScraper.py
│   ├── SteamSpyScraper.py
│   ├── FileSystem.py
│   └── data_integrity.py
```

**New (MVC Pattern):**
```
├── main.py (dashboard only)
├── validate_data.py (CLI tool)
├── ui/
│   ├── scraper.py (scraper control)
│   ├── validator.py (validation tool)
│   └── visualization.py (analysis & viz)
├── src/
│   ├── core/
│   │   ├── scraper.py (BaseScraper)
│   │   └── rate_limiter.py (RateLimiter)
│   ├── scrapers/
│   │   └── steamspy.py (SteamSpyScraper)
│   ├── storage/
│   │   └── filesystem.py (FileSystem)
│   ├── validation/
│   │   └── integrity.py (DataValidator)
│   └── models/
│       └── types.py (ScrapingResult, ValidationResult)
└── _archived/
    ├── scraping.py
    ├── visualization.py
    ├── visualization_multi.py
    └── ... (old files)
```

### Import Changes

**Old:**
```python
from src.FileSystem import FileSystem
from src.BaseScraper import BaseScraper
from src.SteamSpyScraper import SteamSpyScraper
from src.data_integrity import check_folder
```

**New:**
```python
from src import FileSystem, BaseScraper, SteamSpyScraper, DataValidator
# or import specific modules:
from src.storage import FileSystem
from src.core import BaseScraper, RateLimiter
from src.scrapers import SteamSpyScraper
from src.validation import DataValidator
from src.models import ScrapingResult, ValidationResult
```

### Core Changes

#### 1. **BaseScraper** (Simplified)
- ❌ Removed: Marimo auto-detection logic (`_setup_progress()`)
- ❌ Removed: `progress_bar()` method (caller handles progress)
- ✅ Added: Returns structured `ScrapingResult` object instead of raw int
- ✅ Added: `session` initialization in `__aenter__`

**Old Usage:**
```python
async with SteamSpyScraper(fs) as scraper:
    total = await scraper.scrape()  # Returns int
    print(f"Scraped {total} apps")
```

**New Usage:**
```python
async with SteamSpyScraper(fs) as scraper:
    result = await scraper.scrape()  # Returns ScrapingResult
    print(result)  # Nicely formatted output
    if result.errors:
        for err in result.errors:
            print(f"  Error: {err}")
```

#### 2. **RateLimiter** (Extracted)
- Now in `src.core.rate_limiter`
- Single source of truth (no duplicates)
- Reusable by any scraper

#### 3. **FileSystem** (Moved)
- Now in `src.storage.filesystem`
- Added optional `custom_date` parameter for testing
- All methods unchanged (same interface)

#### 4. **Data Validation** (Refactored)
- Old: `check_folder()` function returning exit codes
- New: `DataValidator` class returning `ValidationResult` objects

**Old Usage:**
```python
from src.data_integrity import check_folder
code = check_folder("Data/2025-12-09")
if code == 0:
    print("Valid!")
```

**New Usage:**
```python
from src.validation import DataValidator
validator = DataValidator("Data/2025-12-09")
result = validator.validate()
if result.is_valid:
    print("Valid!")
    print(f"Stats: {result.stats}")
```

### CLI Usage

**Old:**
```powershell
python -m src.data_integrity --path Data/2025-12-09
```

**New:**
```powershell
python validate_data.py --path Data/2025-12-09
python validate_data.py -p Data/2025-12-09  # Short form
```

## Benefits of New Architecture

| Aspect | Before | After |
|--------|--------|-------|
| **Dependencies** | Marimo spreads through core | Zero marimo in core modules |
| **Reusability** | Tightly coupled to notebooks | Pure Python, easily testable |
| **Code duplication** | RateLimiter in 2 places | Single source of truth |
| **Progress handling** | Auto-detect marimo/tqdm | Explicit (caller decides) |
| **Return types** | Raw integers | Structured dataclasses |
| **Testing** | Difficult | Easy (no side effects) |
| **Extensibility** | Hard (mixed concerns) | Easy (clear separation) |

## Running the New System

### Option 1: Dashboard (Recommended)
```powershell
uv run marimo main.py
```
Access individual modules through the dashboard.

### Option 2: Individual Modules
```powershell
uv run marimo ui/scraper.py      # Just scraping
uv run marimo ui/validator.py    # Just validation
uv run marimo ui/visualization.py # Just analysis
```

### Option 3: CLI Tools
```powershell
python validate_data.py --path Data/2025-12-09
```

## Adding a New Scraper

1. Create `src/scrapers/newsource.py`:
```python
from src.core import BaseScraper
from src.models import ScrapingResult

class NewScraper(BaseScraper):
    async def scrape(self) -> ScrapingResult:
        # Your scraping logic
        return ScrapingResult(
            total_scraped=count,
            new_apps=new_count,
            errors=[],
            start_time=self.start_time,
            end_time=datetime.now(),
            metadata={}
        )
```

2. Export in `src/scrapers/__init__.py`:
```python
from .newsource import NewScraper
__all__ = ["SteamSpyScraper", "NewScraper"]
```

3. Use in marimo:
```python
from src.scrapers import NewScraper
async with NewScraper(fs) as scraper:
    result = await scraper.scrape()
```

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'src'`:
- Make sure you're running from the project root
- Try: `python -m src.validation.integrity --help`

### Marimo can't find modules
- Restart marimo: `uv run marimo`
- Clear cache: `rm -r __pycache__ __marimo__`

### Old code references
- `src.data_integrity` → `src.validation.DataValidator`
- `src.BaseScraper` → `src.core.BaseScraper`
- `src.FileSystem` → `src.storage.FileSystem`

## Migration Checklist

- [x] Directory structure created
- [x] Core modules implemented
- [x] SteamSpyScraper refactored
- [x] FileSystem moved and updated
- [x] DataValidator refactored
- [x] Main dashboard created
- [x] UI modules created
- [x] CLI validator created
- [x] Tests updated
- [x] README updated
- [x] Old files archived
