"""
BaseScraper - Abstract base class for all scrapers.
"""
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Set, Callable, List, Any
import aiohttp
from tqdm.auto import tqdm
from datetime import datetime

from .FileSystem import FileSystem


class BaseScraper(ABC):
    """Base class for all web scrapers."""
    
    def __init__(self, filesystem: FileSystem, suppress_output: bool = False):
        """
        Initialize scraper with filesystem.
        
        Args:
            filesystem: FileSystem instance for I/O operations
            suppress_output: If True, suppress print statements
        """
        self.fs = filesystem
        self.session: Optional[aiohttp.ClientSession] = None
        self.start_time = datetime.now()
        self.suppress_output = suppress_output
    
    def _print(self, *args, **kwargs):
        """Print only if output is not suppressed."""
        if not self.suppress_output:
            print(*args, **kwargs)
    
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
        return tqdm(iterable, desc=desc)
    
    async def process_items_in_batches(
        self,
        items: List[Any],
        process_func: Callable,
        batch_label: str = "Batch",
        progress_callback: Optional[Callable] = None,
        batch_delay: Optional[float] = None
    ) -> int:
        """
        Process a list of items with optional progress tracking and delays.
        
        Args:
            items: List of items to process
            process_func: Async function to process each item
            batch_label: Label for progress updates
            progress_callback: Optional callback(current, total, label) for progress
            batch_delay: Optional delay after processing all items
            
        Returns:
            Number of items successfully processed
        """
        processed_count = 0
        
        for i, item in enumerate(items):
            if progress_callback:
                progress_callback(i, len(items), batch_label)
            
            result = await process_func(item)
            if result is not None:
                processed_count += 1
        
        if batch_delay and batch_delay > 0:
            await asyncio.sleep(batch_delay)
        
        return processed_count