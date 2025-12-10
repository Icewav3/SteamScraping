"""Data types and models for the scraper."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any


@dataclass
class ScrapingResult:
    """Result of a scraping operation."""

    total_scraped: int
    """Total number of apps scraped in this session."""

    new_apps: int
    """Number of new apps (not previously scraped)."""

    errors: List[str] = field(default_factory=list)
    """List of error messages encountered."""

    start_time: datetime = field(default_factory=datetime.now)
    """When the scraping started."""

    end_time: datetime = field(default_factory=datetime.now)
    """When the scraping ended."""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """Additional metadata about the scraping run."""

    def __str__(self) -> str:
        elapsed = (self.end_time - self.start_time).total_seconds()
        return (
            f"✓ Scraping Complete!\n"
            f"  Total scraped: {self.total_scraped}\n"
            f"  New apps: {self.new_apps}\n"
            f"  Errors: {len(self.errors)}\n"
            f"  Time elapsed: {elapsed:.1f}s"
        )


@dataclass
class ValidationResult:
    """Result of data validation."""

    is_valid: bool
    """Whether all validations passed."""

    errors: List[str] = field(default_factory=list)
    """List of validation errors."""

    warnings: List[str] = field(default_factory=list)
    """List of validation warnings (non-blocking)."""

    files_found: Dict[str, bool] = field(default_factory=dict)
    """Which required files were found."""

    stats: Dict[str, int] = field(default_factory=dict)
    """Statistics about the data (lines checked, etc)."""

    def __str__(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        msg = f"{status}\n"
        if self.errors:
            msg += f"  Errors: {len(self.errors)}\n"
            for err in self.errors[:5]:
                msg += f"    - {err}\n"
            if len(self.errors) > 5:
                msg += f"    ... and {len(self.errors) - 5} more\n"
        if self.warnings:
            msg += f"  Warnings: {len(self.warnings)}\n"
            for warn in self.warnings[:3]:
                msg += f"    - {warn}\n"
        if self.stats:
            msg += "  Stats:\n"
            for key, val in self.stats.items():
                msg += f"    {key}: {val}\n"
        return msg
