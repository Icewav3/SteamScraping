"""
data_integrity.py
Simple data integrity checker for scraped data folders.

Checks that:
 - required files exist
 - JSONL lines parse as JSON and have 'appid' field
 - scraped_appids.txt lines are unique integers
 - metadata file exists and contains expected keys

Usage:
    python -m src.data_integrity --path ./Data/2025-11-11

"""
from __future__ import annotations
import argparse
import json
import os
from typing import Tuple

REQUIRED_FILES = [
    "steamspy_data.jsonl",
    "scraped_appids.txt",
    "metadata.json",
]


def check_jsonl_file(path: str) -> Tuple[int, int]:
    """Validate JSON Lines file.

    Returns (lines_checked, errors_found)
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
                # basic validation
                if not isinstance(obj, dict) or "appid" not in obj:
                    errors += 1
            except json.JSONDecodeError:
                errors += 1
    return lines, errors


def check_scraped_appids(path: str) -> Tuple[int, int]:
    """Validate scraped_appids.txt contains unique integers.

    Returns (lines_checked, errors_found)
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


def check_metadata(path: str) -> Tuple[bool, str]:
    """Check that metadata file exists and contains common keys.

    Returns (valid, message)
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


def check_folder(folder_path: str) -> int:
    """Perform all checks on a folder. Return non-zero exit code on error."""
    exit_code = 0
    print(f"Checking folder: {folder_path}")
    for fname in REQUIRED_FILES:
        full = os.path.join(folder_path, fname)
        exists = os.path.exists(full)
        print(f" - {fname}: {'FOUND' if exists else 'MISSING'}")
        if not exists:
            exit_code = 2
    # JSONL check
    lines, errs = check_jsonl_file(os.path.join(folder_path, "steamspy_data.jsonl"))
    print(f" - steamspy_data.jsonl: lines={lines}, errors={errs}")
    if errs:
        exit_code = max(exit_code, 3)
    # scraped appids
    lines, errs = check_scraped_appids(os.path.join(folder_path, "scraped_appids.txt"))
    print(f" - scraped_appids.txt: lines={lines}, errors={errs}")
    if errs:
        exit_code = max(exit_code, 4)
    # metadata
    valid, msg = check_metadata(os.path.join(folder_path, "metadata.json"))
    print(f" - metadata.json: {msg}")
    if not valid:
        exit_code = max(exit_code, 5)
    return exit_code


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", "-p", required=True, help="Path to daily data folder (e.g. Data/2025-11-11)")
    args = parser.parse_args()
    folder = args.path
    if not os.path.isdir(folder):
        print(f"Not a folder: {folder}")
        raise SystemExit(2)
    code = check_folder(folder)
    if code == 0:
        print("All checks passed ✅")
    else:
        print(f"Checks failed with exit code {code} ⚠️")
    raise SystemExit(code)


if __name__ == "__main__":
    main()
