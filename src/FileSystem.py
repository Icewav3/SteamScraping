# src/FileSystem.py
"""FileSystem - Simplified for scraper-specific directories with atomic writes."""
import json
import os
from typing import Set, Dict, Any, Optional
from datetime import datetime
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
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.daily_dir = self.data_dir / self.today / scraper_name
        self.daily_dir.mkdir(parents=True, exist_ok=True)
    
    def get_output_path(self, filename: str) -> Path:
        """Get full path for output file."""
        return self.daily_dir / filename
    
    def append_jsonl(self, data: Dict[str, Any], filename: str):
        """
        Append JSON line to file atomically.
        """
        target_path = self.get_output_path(filename)
        
        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.daily_dir,
            prefix=f'.{filename}.',
            suffix='.tmp',
            text=True
        )
        
        try:
            # Write the JSON line to temp file
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                json.dump(data, f)
                f.write('\n')
                f.flush()
                os.fsync(f.fileno())  # Force write to disk
            
            # Atomically append to target (this is atomic on POSIX)
            with open(temp_path, 'r', encoding='utf-8') as src:
                with open(target_path, 'a', encoding='utf-8') as dst:
                    dst.write(src.read())
                    dst.flush()
                    os.fsync(dst.fileno())
        finally:
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except OSError:
                pass
    
    def append_line(self, line: str, filename: str):
        """
        Append text line atomically.
        """
        target_path = self.get_output_path(filename)
        
        # Write to temporary file first
        temp_fd, temp_path = tempfile.mkstemp(
            dir=self.daily_dir,
            prefix=f'.{filename}.',
            suffix='.tmp',
            text=True
        )
        
        try:
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as f:
                f.write(f"{line}\n")
                f.flush()
                os.fsync(f.fileno())
            
            # Atomically append to target
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
    
    def read_lines(self, filename: str) -> Set[str]:
        """Read all lines as set."""
        path = self.get_output_path(filename)
        if not path.exists():
            return set()
        return set(line.strip() for line in path.read_text().splitlines() if line.strip())
    
    def save_json(self, data: Dict[str, Any], filename: str):
        target_path = self.get_output_path(filename)
        
        # Write to temporary file first
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
            
            # Atomic rename (this is atomic on POSIX)
            shutil.move(temp_path, target_path)
        except:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise