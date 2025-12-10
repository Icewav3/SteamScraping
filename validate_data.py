#!/usr/bin/env python
"""
Command-line interface for data validation.

Maintains backward compatibility with the old data_integrity module.
"""

import argparse
import sys
from src.validation import DataValidator


def main():
    parser = argparse.ArgumentParser(
        description="Validate scraped data folders"
    )
    parser.add_argument(
        "--path",
        "-p",
        required=True,
        help="Path to daily data folder (e.g. Data/2025-11-11)",
    )
    args = parser.parse_args()

    folder = args.path

    # Run validation
    validator = DataValidator(folder)
    result = validator.validate()

    # Print report
    print()
    print(validator.get_report())

    # Return appropriate exit code
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
