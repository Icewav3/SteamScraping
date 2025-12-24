# src/FileSystem.py
"""FileSystem - Simplified for scraper-specific directories."""
import json
import os
from typing import Set, Dict, Any, Optional
from datetime import datetime
from pathlib import Path


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
        """Append JSON line to file."""
        with open(self.get_output_path(filename), 'a', encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')
    
    def append_line(self, line: str, filename: str):
        """Append text line."""
        with open(self.get_output_path(filename), 'a', encoding='utf-8') as f:
            f.write(f"{line}\n")
    
    def read_lines(self, filename: str) -> Set[str]:
        """Read all lines as set."""
        path = self.get_output_path(filename)
        if not path.exists():
            return set()
        return set(line.strip() for line in path.read_text().splitlines() if line.strip())
    
    def save_json(self, data: Dict[str, Any], filename: str):
        """Save formatted JSON."""
        with open(self.get_output_path(filename), 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)