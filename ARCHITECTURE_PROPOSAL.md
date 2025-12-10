# SteamScraping - Refactored Architecture Proposal

## Current State Analysis

### Problems Identified

1. **Code Duplication**
   - `scraping.py` is a messy notebook file with duplicate functionality from `src/SteamSpyScraper.py`
   - Multiple logging/progress functions scattered across files
   - `RateLimiter` defined in both `scraping.py` and `SteamSpyScraper.py`

2. **Mixed Concerns**
   - `BaseScraper` tries to auto-detect progress bars (marimo, tqdm) which adds unnecessary complexity
   - `main.py` has nested marimo apps (confusing structure)
   - `visualization.py` is incomplete and standalone

3. **Incomplete Implementation**
   - `visualization_multi.py` exists but not included in analysis
   - Progress bar handling is overly complex for what's needed
   - `progress_bar()` method referenced in `SteamSpyScraper` but not defined in `BaseScraper`

4. **Testing & Validation**
   - Only basic data integrity tests exist
   - No tests for scrapers themselves
   - Data integrity checker is CLI-only, not integrated

5. **File Organization**
   - Two separate marimo apps (`main.py`, `visualization.py`) with separate concerns
   - Old notebook files (`LegacyScraper.ipynb`, `visualization.ipynb`) taking up space
   - Scripts folder has minimal content

---

## Proposed Architecture

### Core Principle: **Marimo as the UI, Python Modules as the Engine**

Instead of mixing logic with marimo cells, separate concerns cleanly:
- **Pure Python modules** in `src/` for business logic
- **Single marimo app** (`main.py`) as the dashboard/UI
- **No dependencies on marimo** in core scraper code

### 1. Simplified Source Structure

```
src/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── scraper.py          # Abstract scraper base class
│   ├── rate_limiter.py      # Reusable rate limiter
│   └── progress.py          # Progress tracking abstraction
├── scrapers/
│   ├── __init__.py
│   └── steamspy.py          # SteamSpy-specific scraper
├── storage/
│   ├── __init__.py
│   └── filesystem.py        # File I/O (moved from root level)
├── validation/
│   ├── __init__.py
│   └── integrity.py         # Data validation (moved from root)
└── models/
    ├── __init__.py
    └── types.py             # Pydantic models for data structures
```

### 2. Key Module Changes

#### **src/core/scraper.py** (Simplified BaseScraper)
```python
class BaseScraper(ABC):
    """Minimal abstract base for all scrapers."""
    
    def __init__(self, filesystem: FileSystem):
        self.fs = filesystem
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self): ...
    async def __aexit__(self, ...): ...
    
    @abstractmethod
    async def scrape(self) -> ScrapingResult: ...
```

**Changes:**
- Remove marimo auto-detection complexity
- Remove progress bar handling (caller responsibility)
- Return structured `ScrapingResult` objects instead of raw ints

#### **src/core/rate_limiter.py** (Extracted & Simplified)
```python
class RateLimiter:
    """Simple, reusable rate limiter."""
    def __init__(self, interval: float): ...
    async def __aenter__(self): ...
    async def __aexit__(self, ...): ...
```

**Changes:**
- Single source of truth (remove duplicate from `SteamSpyScraper`)
- Importable by any scraper

#### **src/scrapers/steamspy.py** (Cleaned SteamSpyScraper)
```python
class SteamSpyScraper(BaseScraper):
    def __init__(self, filesystem, pages=10, page_delay=60, app_delay=0.1): ...
    async def scrape(self) -> ScrapingResult: ...
```

**Changes:**
- Remove internal `RateLimiter` definition, import from `core`
- Return `ScrapingResult` dataclass with structured data
- Keep rate limiting and API logic

#### **src/storage/filesystem.py** (Renamed from FileSystem.py)
```python
class FileSystem:
    """Handles file I/O for scrapers."""
    def __init__(self, data_dir: str = "Data", custom_date: Optional[str] = None): ...
```

**Changes:**
- Allow optional custom date (useful for testing)
- Keep existing methods (simple and effective)

#### **src/validation/integrity.py** (Refactored data_integrity.py)
```python
class DataValidator:
    """Validates scraped data folders."""
    
    def __init__(self, folder_path: str): ...
    def validate(self) -> ValidationResult: ...
    def get_report(self) -> str: ...
```

**Changes:**
- Object-oriented instead of functional
- Return structured `ValidationResult` objects
- Keep CLI entry point for command-line use

#### **src/models/types.py** (New)
```python
@dataclass
class ScrapingResult:
    total_scraped: int
    new_apps: int
    errors: List[str]
    start_time: datetime
    end_time: datetime
    metadata: dict

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    files_found: Dict[str, bool]
    stats: Dict[str, int]
```

### 3. Marimo App Structure (main.py)

**Single, cohesive dashboard with logical sections:**

```python
import marimo
from src.scrapers.steamspy import SteamSpyScraper
from src.storage.filesystem import FileSystem
from src.validation.integrity import DataValidator

app = marimo.App()

# Section 1: Header
@app.cell
def header(mo): ...

# Section 2: Scraper Controls
@app.cell
async def scraper_section(mo, FileSystem, SteamSpyScraper): ...

# Section 3: Data Integrity Checker
@app.cell
def integrity_section(mo, DataValidator): ...

# Section 4: Quick Visualization
@app.cell
def viz_section(mo, pd): ...
```

**Benefits:**
- All controls in one place
- Marimo handles reactivity naturally
- Easy to add/remove features
- Clear visual flow

### 4. Visualization Strategy

**Option A: Keep separate visualization.py**
- Create lightweight analytics-focused marimo file
- Import data directly from `Data/` folder
- Use pandas for analysis

**Option B: Merge into main.py**
- Add a "Visualization" section to dashboard
- Add collapsible/tabs for different views
- Keep marimo reactive UI management

**Recommendation:** Keep separate for now (Option A) but refactor to:
- Remove hardcoded dates
- Add date range selector
- Create reusable analysis functions

### 5. Testing

Create `tests/` directory:
```
tests/
├── __init__.py
├── test_scraper.py          # Test SteamSpyScraper logic
├── test_rate_limiter.py     # Test rate limiting
├── test_filesystem.py       # Test file operations
└── test_integrity.py        # Test validation
```

**Note:** Keep mock/stub APIs to avoid hitting real SteamSpy API during tests

---

## Migration Path (If Approved)

### Phase 1: Restructure (Low risk)
1. Create new `src/core/`, `src/scrapers/`, `src/storage/`, `src/validation/` directories
2. Move & refactor files into new structure
3. Create `src/models/types.py` with dataclasses
4. Update imports in `main.py`
5. Delete `scraping.py`, `visualization.py` (keep logic, move to new locations)
6. Archive old notebooks to `_archived/` folder

### Phase 2: Simplify (Medium risk)
1. Simplify `BaseScraper` (remove marimo detection)
2. Extract `RateLimiter` to `core/rate_limiter.py`
3. Update `SteamSpyScraper` to use new structure
4. Implement structured result objects (`ScrapingResult`, `ValidationResult`)

### Phase 3: Integrate (Medium risk)
1. Update `main.py` to use new modules
2. Refactor `data_integrity.py` into `validation/integrity.py`
3. Test CLI still works: `python -m src.validation.integrity --path Data/2025-11-11`

### Phase 4: Polish (Low risk)
1. Add comprehensive docstrings
2. Set up pytest
3. Create tests for core modules
4. Update README with new structure

---

## Benefits of This Architecture

| Aspect | Current | Proposed |
|--------|---------|----------|
| **Code Duplication** | High (RateLimiter, logging in 2+ places) | None (single source of truth) |
| **Marimo Dependency** | Spreads through core logic | Isolated to UI layer |
| **Testability** | Hard (mixed concerns) | Easy (pure functions/classes) |
| **Reusability** | Low (tightly coupled) | High (modules are independent) |
| **Maintainability** | Difficult (scattered code) | Easy (clear organization) |
| **Extensibility** | Hard (would require duplicating patterns) | Easy (just extend BaseScraper) |

---

## What Gets Cut

1. **scraping.py** - Duplicate/messy notebook code
2. **visualization.py (current)** - Superseded by cleaner version or dashboard integration
3. **RateLimiter duplication** - Single implementation in `core/`
4. **Progress bar auto-detection** - Caller handles (simpler, explicit)
5. **Old notebooks** - Archive to `_archived/`

---

## What Stays

1. **Core scraping logic** - Proven and working
2. **File I/O patterns** - Simple and effective
3. **Data integrity checking** - Valuable, just reorganized
4. **Async/await patterns** - Already good
5. **SteamSpy API integration** - Solid implementation

---

## Open Questions

1. **visualization.py vs. integrated dashboard?** Keep separate or merge into main.py?
2. **visualization_multi.py** - What does this do? Should it be kept/refactored?
3. **Test coverage requirements** - How extensive?
4. **Future scraper sources** - Plan to add more (e.g., Steam Store API)?

---

## Estimated Effort

- **Phase 1:** ~2-3 hours
- **Phase 2:** ~1-2 hours  
- **Phase 3:** ~1-2 hours
- **Phase 4:** ~1-2 hours

**Total:** ~6-9 hours of work

---

**Ready to proceed? Let me know if you'd like any changes to this proposal!**
