"""Dataset validation script — checks schema, missing values, negative values, duplicates.

Usage:
    python scripts/validate_datasets.py                    # Validates data/demo and data/templates
    python scripts/validate_datasets.py --path file.csv   # Single file
    python scripts/validate_datasets.py --dir data/raw    # All CSVs in a directory
"""
from __future__ import annotations
import argparse
import hashlib
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "data" / "demo"
TEMPLATE_DIR = ROOT / "data" / "templates"

COLUMN_SCHEMAS = {
    "electricity": {
        "required": ["timestamp", "building_id", "consumption_kwh"],
        "numeric": ["consumption_kwh", "occupancy_count", "floor_area_m2"],
        "date_col": "timestamp",
    },
    "water": {
        "required": ["measurement_date", "building_id", "consumption_litres"],
        "numeric": ["consumption_litres", "occupancy_count"],
        "date_col": "measurement_date",
    },
    "waste": {
        "required": ["measurement_date", "building_id", "total_waste_kg"],
        "numeric": ["total_waste_kg", "wet_waste_kg", "dry_recyclable_kg", "residual_waste_kg"],
        "date_col": "measurement_date",
    },
}


def detect_schema(df: pd.DataFrame) -> str | None:
    cols = set(df.columns.str.lower())
    for name, schema in COLUMN_SCHEMAS.items():
        if set(schema["required"]).issubset(cols):
            return name
    return None


def file_checksum(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def validate_file(path: Path) -> dict:
    print(f"\nValidating: {path.name}")
    print("-" * 60)
    result = {"file": str(path), "exists": path.exists(), "issues": [], "warnings": [], "pass": False}

    if not path.exists():
        print(f"  MISSING: {path}")
        result["issues"].append("File not found.")
        return result

    size_kb = path.stat().st_size / 1024
    sha = file_checksum(path)
    print(f"  Size: {size_kb:.1f} KB | SHA256: {sha}")

    try:
        df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_excel(path)
    except Exception as e:
        result["issues"].append(f"Parse error: {e}")
        return result

    df.columns = df.columns.str.strip().str.lower()
    print(f"  Rows: {len(df)} | Columns: {list(df.columns)}")

    schema_name = detect_schema(df)
    if schema_name:
        print(f"  Schema match: {schema_name}")
        schema = COLUMN_SCHEMAS[schema_name]

        missing_cols = [c for c in schema["required"] if c not in df.columns]
        if missing_cols:
            result["issues"].append(f"Missing required columns: {missing_cols}")
        else:
            print(f"  Required columns: OK")

        for col in schema["required"]:
            if col in df.columns:
                null_count = int(df[col].isnull().sum())
                if null_count > 0:
                    result["warnings"].append(f"{null_count} missing values in '{col}'")
                    print(f"  WARN: {null_count} nulls in '{col}'")

        for col in schema["numeric"]:
            if col in df.columns:
                neg_count = int((pd.to_numeric(df[col], errors="coerce") < 0).sum())
                if neg_count > 0:
                    result["issues"].append(f"{neg_count} negative values in '{col}'")
                    print(f"  ERROR: {neg_count} negatives in '{col}'")

        date_col = schema["date_col"]
        if date_col in df.columns and "building_id" in df.columns:
            dupes = int(df.duplicated(subset=[date_col, "building_id"]).sum())
            if dupes > 0:
                result["warnings"].append(f"{dupes} duplicate (date, building_id) pairs")
                print(f"  WARN: {dupes} duplicate rows")

        if date_col in df.columns:
            try:
                dates = pd.to_datetime(df[date_col])
                print(f"  Date range: {dates.min().date()} to {dates.max().date()}")
            except Exception:
                result["warnings"].append("Could not parse date column.")
    else:
        result["warnings"].append("Could not match a known schema (electricity/water/waste).")
        print("  WARN: Unknown schema")

    if "is_synthetic" in df.columns:
        pct = df["is_synthetic"].sum() / len(df) * 100
        print(f"  Synthetic rows: {pct:.1f}%")

    result["pass"] = len(result["issues"]) == 0
    status = "PASS" if result["pass"] else "FAIL"
    print(f"  Result: {status}")
    for issue in result["issues"]:
        print(f"    ERROR: {issue}")
    for w in result["warnings"]:
        print(f"    WARN:  {w}")
    return result


def main():
    parser = argparse.ArgumentParser(description="Validate campus dataset files.")
    parser.add_argument("--path", help="Single file path to validate")
    parser.add_argument("--dir", help="Directory of files to validate")
    args = parser.parse_args()

    paths = []
    if args.path:
        paths = [Path(args.path)]
    elif args.dir:
        d = Path(args.dir)
        paths = list(d.glob("*.csv")) + list(d.glob("*.xlsx"))
    else:
        paths = list(DEMO_DIR.glob("*.csv")) + list(TEMPLATE_DIR.glob("*.csv"))

    if not paths:
        print("No files found to validate.")
        sys.exit(0)

    print(f"Dataset Validation Report -- {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    results = [validate_file(p) for p in paths]
    passed = sum(1 for r in results if r["pass"])
    failed = len(results) - passed
    print(f"\nSummary: {passed} passed, {failed} failed out of {len(results)} files.")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
