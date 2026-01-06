# src/FileSystem.py
"""FileSystem - Simplified for scraper-specific directories with atomic writes."""
import json
import os
from typing import Set, Dict, Any, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import shutil


class FileSystem:
    """Manages file operations with scraper-specific directories."""
    
    def __init__(self, data_dir: str = "Data", scraper_name: str = "UnknownScraper"):
        """
        Args:
            data_dir: Base directory (Data/)
            scraper_name: Name of scraper (e.g., "SteamSpyScraper")
        """
        self.data_dir = Path(data_dir)
        self.scraper_name = scraper_name
        self.today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.daily_dir = self.data_dir / self.today / scraper_name
        self.daily_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for output file with scraper prefix."""
        prefix = self.scraper_name.replace("Scraper", "").lower() + "_"
        prefixed_filename = prefix + filename if not filename.startswith(prefix) else filename
        return self.daily_dir / prefixed_filename
    
    def _atomic_append(self, filename: str, write_func: Callable[[Any], None]):
        """
        Atomically append content to file using temp file pattern.
        
        Args:
            filename: Target file name
            write_func: Function that writes to a file object
        """
        target_path = self.get_output_path(filename)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.daily_dir,
            prefix=f'.{filename}.',
            suffix='.tmp',
            text=True
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                write_func(f)
                f.flush()
                os.fsync(f.fileno())
            
            with open(temp_path, 'r', encoding='utf-8') as src:
                with open(target_path, 'a', encoding='utf-8') as dst:
                    dst.write(src.read())
                    dst.flush()
                    os.fsync(dst.fileno())
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    def append_jsonl(self, data: Dict[str, Any], filename: str):
        """Append JSON line to file atomically."""
        self._atomic_append(filename, lambda f: (
            json.dump(data, f),
            f.write('\n')
        ))
    
    def append_line(self, line: str, filename: str):
        """Append text line atomically."""
        self._atomic_append(filename, lambda f: f.write(f"{line}\n"))
    
    def read_lines(self, filename: str) -> Set[str]:
        """Read all lines as set."""
        path = self.get_output_path(filename)
        if not path.exists():
            return set()
        return set(line.strip() for line in path.read_text().splitlines() if line.strip())
    
    def save_json(self, data: Dict[str, Any], filename: str):
        """Save formatted JSON with atomic write."""
        target_path = self.get_output_path(filename)
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.daily_dir,
            prefix=f'.{filename}.',
            suffix='.tmp',
            text=True
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            
            shutil.move(temp_path, target_path)
        except:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise