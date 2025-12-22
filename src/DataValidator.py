"""
Streamlined Data Validator for scraped game data.
Focuses on actionable validation with clear error reporting.
"""
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class ValidationIssue:
    """Single validation issue with context."""
    level: str  # 'error' or 'warning'
    source: str  # 'steamspy', 'rawg', 'cross_source'
    message: str
    record_id: Optional[str] = None
    field: Optional[str] = None
    value: Optional[Any] = None


@dataclass
class ValidationReport:
    """Clean validation report with stats and issues."""
    date: str
    issues: List[ValidationIssue] = field(default_factory=list)
    stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def errors(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'error']
    
    @property
    def warnings(self) -> List[ValidationIssue]:
        return [i for i in self.issues if i.level == 'warning']
    
    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0
    
    def print_summary(self, verbose: bool = False):
        """Print human-readable summary."""
        print(f"\n{'='*60}")
        print(f"VALIDATION REPORT - {self.date}")
        print(f"{'='*60}")
        print(f"Status: {'✓ PASSED' if self.is_valid else '✗ FAILED'}")
        print(f"Errors: {len(self.errors)} | Warnings: {len(self.warnings)}")
        
        if self.stats:
            print(f"\nStats:")
            for key, val in self.stats.items():
                print(f"  {key}: {val}")
        
        if self.errors:
            print(f"\n{'='*60}")
            print("ERRORS:")
            for err in self.errors[:20]:
                loc = f" [{err.record_id}]" if err.record_id else ""
                print(f"  ✗ {err.source}: {err.message}{loc}")
            if len(self.errors) > 20:
                print(f"  ... and {len(self.errors) - 20} more")
        
        if verbose and self.warnings:
            print(f"\n{'='*60}")
            print("WARNINGS:")
            for warn in self.warnings[:20]:
                loc = f" [{warn.record_id}]" if warn.record_id else ""
                print(f"  ⚠ {warn.source}: {warn.message}{loc}")
            if len(self.warnings) > 20:
                print(f"  ... and {len(self.warnings) - 20} more")
        
        print(f"{'='*60}\n")


class DataValidator:
    """Validates scraped game data."""
    
    # Schema definitions
    STEAMSPY_REQUIRED = {'appid', 'name'}
    STEAMSPY_EXPECTED = {'developer', 'publisher', 'owners', 'genre', 'tags'}
    
    RAWG_REQUIRED = {'rawg_id', 'name'}
    RAWG_EXPECTED = {'rating', 'genres', 'platforms', 'released'}
    
    def __init__(self, data_dir: str = "Data", date: Optional[str] = None):
        self.data_dir = Path(data_dir)
        self.date = date or datetime.now().strftime("%Y-%m-%d")
        self.daily_dir = self.data_dir / self.date
        self.report = ValidationReport(date=self.date)
    
    def validate(self) -> ValidationReport:
        """Run all validations and return report."""
        if not self.daily_dir.exists():
            self.report.issues.append(ValidationIssue(
                level='error',
                source='system',
                message=f"Data directory not found: {self.daily_dir}"
            ))
            return self.report
        
        # Validate each source
        self._validate_steamspy()
        self._validate_rawg()
        self._validate_cross_source()
        
        return self.report
    
    def _validate_steamspy(self):
        """Validate SteamSpy data."""
        path = self.daily_dir / "steamspy_data.jsonl"
        
        if not path.exists():
            self.report.issues.append(ValidationIssue(
                level='warning', source='steamspy',
                message="Data file not found"
            ))
            return
        
        records = self._load_jsonl(path)
        appids = set()
        valid_count = 0
        
        for idx, rec in enumerate(records):
            record_id = f"line_{idx+1}"
            
            # Check required fields
            missing_required = self.STEAMSPY_REQUIRED - rec.keys()
            if missing_required:
                self.report.issues.append(ValidationIssue(
                    level='error', source='steamspy',
                    message=f"Missing required fields: {missing_required}",
                    record_id=record_id
                ))
                continue
            
            # Check expected fields (non-critical)
            missing_expected = self.STEAMSPY_EXPECTED - rec.keys()
            if missing_expected:
                self.report.issues.append(ValidationIssue(
                    level='warning', source='steamspy',
                    message=f"Missing expected fields: {missing_expected}",
                    record_id=record_id
                ))
            
            # Validate appid
            appid = rec.get('appid')
            if not isinstance(appid, int) or appid <= 0:
                self.report.issues.append(ValidationIssue(
                    level='error', source='steamspy',
                    message=f"Invalid appid: {appid}",
                    record_id=record_id, field='appid', value=appid
                ))
            elif appid in appids:
                self.report.issues.append(ValidationIssue(
                    level='error', source='steamspy',
                    message=f"Duplicate appid: {appid}",
                    record_id=record_id
                ))
            else:
                appids.add(appid)
            
            # Validate owners format
            owners = rec.get('owners')
            if owners and isinstance(owners, str):
                if '..' not in owners and owners != '0':
                    self.report.issues.append(ValidationIssue(
                        level='warning', source='steamspy',
                        message=f"Unusual owners format: {owners}",
                        record_id=record_id, field='owners'
                    ))
            
            # Validate tags structure
            tags = rec.get('tags')
            if tags is not None and not isinstance(tags, dict):
                self.report.issues.append(ValidationIssue(
                    level='error', source='steamspy',
                    message=f"Tags must be dict, got {type(tags).__name__}",
                    record_id=record_id, field='tags'
                ))
            
            valid_count += 1
        
        self.report.stats['steamspy_total'] = len(records)
        self.report.stats['steamspy_unique_appids'] = len(appids)
        self.report.stats['steamspy_valid'] = valid_count
    
    def _validate_rawg(self):
        """Validate RAWG data."""
        path = self.daily_dir / "rawg_data.jsonl"
        
        if not path.exists():
            self.report.issues.append(ValidationIssue(
                level='warning', source='rawg',
                message="Data file not found"
            ))
            return
        
        records = self._load_jsonl(path)
        rawg_ids = set()
        valid_count = 0
        
        for idx, rec in enumerate(records):
            record_id = f"line_{idx+1}"
            
            # Check required fields
            missing_required = self.RAWG_REQUIRED - rec.keys()
            if missing_required:
                self.report.issues.append(ValidationIssue(
                    level='error', source='rawg',
                    message=f"Missing required fields: {missing_required}",
                    record_id=record_id
                ))
                continue
            
            # Check for duplicates
            rawg_id = rec.get('rawg_id')
            if rawg_id in rawg_ids:
                self.report.issues.append(ValidationIssue(
                    level='error', source='rawg',
                    message=f"Duplicate rawg_id: {rawg_id}",
                    record_id=record_id
                ))
            else:
                rawg_ids.add(rawg_id)
            
            # Validate rating (0-5)
            rating = rec.get('rating')
            if rating is not None:
                try:
                    val = float(rating)
                    if not 0 <= val <= 5:
                        self.report.issues.append(ValidationIssue(
                            level='error', source='rawg',
                            message=f"Rating out of range [0-5]: {val}",
                            record_id=record_id, field='rating', value=val
                        ))
                except (ValueError, TypeError):
                    self.report.issues.append(ValidationIssue(
                        level='error', source='rawg',
                        message=f"Invalid rating format: {rating}",
                        record_id=record_id, field='rating'
                    ))
            
            # Validate metacritic (0-100)
            metacritic = rec.get('metacritic')
            if metacritic is not None:
                try:
                    val = int(metacritic)
                    if not 0 <= val <= 100:
                        self.report.issues.append(ValidationIssue(
                            level='error', source='rawg',
                            message=f"Metacritic out of range [0-100]: {val}",
                            record_id=record_id, field='metacritic', value=val
                        ))
                except (ValueError, TypeError):
                    pass  # Skip if not present
            
            # Validate list fields
            for field in ['genres', 'platforms', 'tags']:
                val = rec.get(field)
                if val is not None and not isinstance(val, list):
                    self.report.issues.append(ValidationIssue(
                        level='error', source='rawg',
                        message=f"{field} must be list, got {type(val).__name__}",
                        record_id=record_id, field=field
                    ))
            
            valid_count += 1
        
        self.report.stats['rawg_total'] = len(records)
        self.report.stats['rawg_unique_ids'] = len(rawg_ids)
        self.report.stats['rawg_valid'] = valid_count
    
    def _validate_cross_source(self):
        """Cross-reference between sources."""
        steamspy_path = self.daily_dir / "steamspy_data.jsonl"
        rawg_path = self.daily_dir / "rawg_data.jsonl"
        
        if not (steamspy_path.exists() and rawg_path.exists()):
            return
        
        steamspy_recs = self._load_jsonl(steamspy_path)
        rawg_recs = self._load_jsonl(rawg_path)
        
        # Normalize names for matching
        steamspy_names = {self._normalize_name(r.get('name', '')) for r in steamspy_recs}
        rawg_names = {self._normalize_name(r.get('name', '')) for r in rawg_recs}
        
        steamspy_names.discard('')
        rawg_names.discard('')
        
        overlap = steamspy_names & rawg_names
        
        if steamspy_names:
            overlap_pct = (len(overlap) / len(steamspy_names)) * 100
            self.report.stats['cross_source_overlap'] = len(overlap)
            self.report.stats['cross_source_overlap_pct'] = f"{overlap_pct:.1f}%"
    
    def _load_jsonl(self, path: Path) -> List[Dict[str, Any]]:
        """Load JSONL file, skipping malformed lines."""
        records = []
        with open(path, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                if line.strip():
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError as e:
                        self.report.issues.append(ValidationIssue(
                            level='error',
                            source='parser',
                            message=f"Malformed JSON at line {line_num}: {e}",
                            record_id=f"line_{line_num}"
                        ))
        return records
    
    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize game name for comparison."""
        return name.lower().strip()


def validate_data(data_dir: str = "Data", date: Optional[str] = None, 
                  verbose: bool = False) -> bool:
    """
    Convenience function to validate data and print report.
    
    Args:
        data_dir: Base data directory
        date: Specific date (defaults to today)
        verbose: Show warnings in output
        
    Returns:
        True if validation passed (no errors)
    """
    validator = DataValidator(data_dir, date)
    report = validator.validate()
    report.print_summary(verbose=verbose)
    return report.is_valid


if __name__ == "__main__":
    import sys
    
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "Data"
    date = sys.argv[2] if len(sys.argv) > 2 else None
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    
    is_valid = validate_data(data_dir, date, verbose)
    sys.exit(0 if is_valid else 1)