"""Data validation and integrity checking."""

import os
import json
from typing import Tuple
from ..models import ValidationResult


class DataValidator:
    """Validates scraped data folders."""

    REQUIRED_FILES = [
        "steamspy_data.jsonl",
        "scraped_appids.txt",
        "metadata.json",
    ]

    def __init__(self, folder_path: str):
        """
        Initialize validator for a folder.

        Args:
            folder_path: Path to the data folder to validate.
        """
        self.folder_path = folder_path
        self.result = ValidationResult(is_valid=True)

    def _check_jsonl_file(self, path: str) -> Tuple[int, int]:
        """
        Validate JSON Lines file.

        Returns:
            (lines_checked, errors_found)
        """
        lines = 0
        errors = 0
        if not os.path.exists(path):
            return 0, 1

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                lines += 1
                try:
                    obj = json.loads(stripped)
                    # Basic validation: should be dict with appid
                    if not isinstance(obj, dict) or "appid" not in obj:
                        errors += 1
                except json.JSONDecodeError:
                    errors += 1

        return lines, errors

    def _check_scraped_appids(self, path: str) -> Tuple[int, int]:
        """
        Validate scraped_appids.txt contains unique integers.

        Returns:
            (lines_checked, errors_found)
        """
        lines = 0
        errors = 0
        seen = set()

        if not os.path.exists(path):
            return 0, 1

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                lines += 1
                try:
                    val = int(stripped)
                    if val in seen:
                        errors += 1
                    else:
                        seen.add(val)
                except ValueError:
                    errors += 1

        return lines, errors

    def _check_metadata(self, path: str) -> Tuple[bool, str]:
        """
        Check that metadata file exists and contains common keys.

        Returns:
            (valid, message)
        """
        if not os.path.exists(path):
            return False, f"{path} does not exist"

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)

            required_keys = ["start_time", "end_time", "apps_scraped"]
            missing = [k for k in required_keys if k not in data]

            if missing:
                return False, f"Missing keys: {missing}"

            return True, "OK"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {e}"

    def validate(self) -> ValidationResult:
        """
        Perform all validation checks on the folder.

        Returns:
            ValidationResult with all findings.
        """
        print(f"Validating folder: {self.folder_path}")
        files_found = {}
        stats = {}

        # Check required files
        for fname in self.REQUIRED_FILES:
            full = os.path.join(self.folder_path, fname)
            exists = os.path.exists(full)
            files_found[fname] = exists
            print(f" - {fname}: {'✓ FOUND' if exists else '✗ MISSING'}")

            if not exists:
                self.result.is_valid = False
                self.result.errors.append(f"Required file missing: {fname}")

        # JSONL check
        jsonl_path = os.path.join(self.folder_path, "steamspy_data.jsonl")
        lines, errs = self._check_jsonl_file(jsonl_path)
        stats["jsonl_lines"] = lines
        stats["jsonl_errors"] = errs
        print(f" - steamspy_data.jsonl: {lines} lines, {errs} errors")

        if errs > 0:
            self.result.is_valid = False
            self.result.errors.append(f"JSONL file has {errs} invalid lines")

        # Scraped appids check
        appids_path = os.path.join(self.folder_path, "scraped_appids.txt")
        lines, errs = self._check_scraped_appids(appids_path)
        stats["appids_count"] = lines
        stats["appids_errors"] = errs
        print(f" - scraped_appids.txt: {lines} apps, {errs} errors")

        if errs > 0:
            self.result.is_valid = False
            self.result.errors.append(f"appids file has {errs} duplicates or invalid entries")

        # Metadata check
        metadata_path = os.path.join(self.folder_path, "metadata.json")
        valid, msg = self._check_metadata(metadata_path)
        print(f" - metadata.json: {msg}")

        if not valid:
            self.result.is_valid = False
            self.result.errors.append(f"Metadata issue: {msg}")

        # Update result
        self.result.files_found = files_found
        self.result.stats = stats

        return self.result

    def get_report(self) -> str:
        """
        Get a human-readable validation report.

        Returns:
            Formatted validation report.
        """
        return str(self.result)
