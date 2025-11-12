"""
FileSystem - Handles all file read/write operations for scrapers.
"""
import json
import os
from typing import Set, Dict, Any, Optional
from datetime import datetime


class FileSystem:
    """Manages all file operations for the scraper."""
    
    def __init__(self, data_dir: str = "Data"):
        """
        Initialize FileSystem with base data directory.
        
        Args:
            data_dir: Base directory for all data files
        """
        self.data_dir = data_dir
        self.today = datetime.now().strftime("%Y-%m-%d")
        self.daily_dir = os.path.join(data_dir, self.today)
        
        # Create directory if it doesn't exist
        os.makedirs(self.daily_dir, exist_ok=True)
    
    def get_output_path(self, filename: str) -> str:
        """Get full path for an output file in today's directory."""
        return os.path.join(self.daily_dir, filename)
    
    def append_jsonl(self, data: Dict[str, Any], filename: str):
        """
        Append JSON data as a new line to JSONL file.
        
        Args:
            data: Dictionary to write as JSON
            filename: Name of JSONL file
        """
        filepath = self.get_output_path(filename)
        with open(filepath, 'a', encoding='utf-8') as f:
            json.dump(data, f)
            f.write('\n')
    
    def append_line(self, line: str, filename: str):
        """
        Append a line of text to file.
        
        Args:
            line: Text line to append
            filename: Name of file
        """
        filepath = self.get_output_path(filename)
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"{line}\n")
    
    def read_lines(self, filename: str) -> Set[str]:
        """
        Read all lines from a file as a set.
        
        Args:
            filename: Name of file to read
            
        Returns:
            Set of lines (stripped of whitespace)
        """
        filepath = self.get_output_path(filename)
        if not os.path.exists(filepath):
            return set()
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    
    def save_json(self, data: Dict[str, Any], filename: str):
        """
        Save dictionary as formatted JSON file.
        
        Args:
            data: Dictionary to save
            filename: Name of JSON file
        """
        filepath = self.get_output_path(filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    
    def load_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """
        Load JSON file as dictionary.
        
        Args:
            filename: Name of JSON file
            
        Returns:
            Dictionary from JSON or None if file doesn't exist
        """
        filepath = self.get_output_path(filename)
        if not os.path.exists(filepath):
            return None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
