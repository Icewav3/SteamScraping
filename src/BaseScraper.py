"""
BaseScraper - Abstract base class for all scrapers.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Set, Iterable
import aiohttp
try:
    # Import optional dependencies lazily if available
    import marimo as _marimo  # type: ignore
except Exception:
    _marimo = None
try:
    from tqdm import tqdm
except Exception:
    tqdm = None  # type: ignore
from datetime import datetime

from .FileSystem import FileSystem


class BaseScraper(ABC):
    """Base class for all web scrapers."""
    
    def __init__(self, filesystem: FileSystem):
        """
        Initialize scraper with filesystem.
        
        Args:
            filesystem: FileSystem instance for I/O operations
        """
        self.fs = filesystem
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = datetime.now()
    
    async def __aenter__(self):
        """Async context manager entry - create session."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - close session."""
        if self.session:
            await self.session.close()
    
    @abstractmethod
    async def scrape(self, **kwargs):
        """
        Main scraping method - must be implemented by subclasses.
        
        Returns:
            Number of items scraped
        """
        pass
    
    def log_error(self, message: str, error_file: str = "errors.log"):
        """
        Log an error message.
        
        Args:
            message: Error message to log
            error_file: Name of error log file
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.fs.append_line(f"[{timestamp}] {message}", error_file)
    
    def save_progress(self, item_id: str, progress_file: str = "progress.txt"):
        """
        Save progress for resumability.
        
        Args:
            item_id: ID of completed item
            progress_file: Name of progress tracking file
        """
        self.fs.append_line(item_id, progress_file)
    
    def load_progress(self, progress_file: str = "progress.txt") -> Set[str]:
        """
        Load previously completed items.
        
        Args:
            progress_file: Name of progress tracking file
            
        Returns:
            Set of completed item IDs
        """
        return self.fs.read_lines(progress_file)
    
    def progress_bar(self, iterable, desc: str):
        """
        Create a progress bar for iterations.
        
        Args:
            iterable: Items to iterate over
            desc: Description text for progress bar
            
        Returns:
            tqdm progress bar
        """
        """
        Create a progress bar for iterations. Uses Marimo's progress display when available
        (so that progress renders inside marimo notebooks), otherwise falls back to tqdm.

        Args:
            iterable: Items to iterate over
            desc: Description text for progress bar

        Returns:
            An iterable wrapper which yields items and displays progress via Marimo or tqdm
        """
        # Prefer marimo progress if running inside a marimo session and it exposes a progress API
        try:
            if _marimo is not None:
                # Different marimo versions expose different helpers; attempt common ones
                if hasattr(_marimo, "progress"):
                    try:
                        return _marimo.progress(iterable, label=desc)
                    except TypeError:
                        # older/newer signatures may use desc instead of label
                        return _marimo.progress(iterable, desc)
                if hasattr(_marimo, "progressbar"):
                    try:
                        return _marimo.progressbar(iterable, label=desc)
                    except TypeError:
                        return _marimo.progressbar(iterable, desc)
        except Exception:
            # If anything goes wrong when attempting to use marimo, fall back to tqdm below
            _marimo = None  # type: ignore

        # Fallback to tqdm if available
        if tqdm is not None:
            return tqdm(iterable, desc=desc)

        # Final fallback: return the raw iterable
        return iterable
