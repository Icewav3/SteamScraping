"""
DataValidator - Uses pandera for schema validation.
Install: uv add pandera[io]
"""
import json
from pathlib import Path
import pandera as pa
from pandera import Column, DataFrameSchema
import pandas as pd


# Schemas
STEAMSPY_SCHEMA = DataFrameSchema({
    "appid": Column(int, nullable=False, unique=True),
    "name": Column(str, nullable=False),
    "developer": Column(str, nullable=True),
    "publisher": Column(str, nullable=True),
    "owners": Column(str, nullable=True),
    "genre": Column(str, nullable=True),
})

RAWG_SCHEMA = DataFrameSchema({
    "rawg_id": Column(int, nullable=False, unique=True),
    "name": Column(str, nullable=False),
    "rating": Column(float, pa.Check.in_range(0, 5), nullable=True),
    "released": Column(str, nullable=True),
})


def validate_file(file_path: Path, schema: DataFrameSchema) -> bool:
    """Validate a JSONL file against schema."""
    try:
        # Read JSONL into DataFrame
        records = []
        with open(file_path) as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
        
        df = pd.DataFrame(records)
        schema.validate(df, lazy=True)
        print(f"✓ {file_path.name}: {len(df)} valid entries")
        return True
    
    except pa.errors.SchemaErrors as e:
        print(f"✗ {file_path.name} validation failed:")
        print(e.failure_cases)
        return False


def validate_data(data_dir: str = "Data") -> bool:
    """Validate all data files."""
    data_path = Path(data_dir)
    
    all_valid = True
    
    # Validate SteamSpy
    steamspy = data_path / "steamspy_latest.jsonl"
    if steamspy.exists():
        all_valid &= validate_file(steamspy, STEAMSPY_SCHEMA)
    else:
        print(f"⚠ {steamspy} not found")
    
    # Validate RAWG
    rawg = data_path / "rawg_latest.jsonl"
    if rawg.exists():
        all_valid &= validate_file(rawg, RAWG_SCHEMA)
    else:
        print(f"⚠ {rawg} not found")
    
    return all_valid


if __name__ == "__main__":
    import sys
    is_valid = validate_data()
    sys.exit(0 if is_valid else 1)