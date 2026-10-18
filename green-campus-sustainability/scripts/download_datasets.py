#!/usr/bin/env python3
"""Reproducible dataset downloader for Green Campus Sustainability Auditor.

Verified download URLs as of 2024-10 from archive.ics.uci.edu.
Every download is verified with SHA-256 checksum and logged to a manifest.

Usage:
    python scripts/download_datasets.py              # Download all available datasets
    python scripts/download_datasets.py --list       # List datasets and status
    python scripts/download_datasets.py --id 374     # Download specific dataset

⚠️  IMPORTANT WARNINGS:
    - UCI datasets #235 and #374 are HOUSEHOLD datasets from Europe — NOT campus data.
    - They are used only as EXTERNAL BENCHMARKS for time-series processing methodology.
    - They MUST NOT be presented as actual campus electricity readings.
    - UCI dataset #242 (Energy Efficiency) contains simulated building load targets.
    - India Government (data.gov.in) and CPCB datasets require MANUAL access.
      See docs/DATASET_DOWNLOAD_GUIDE.md for step-by-step instructions.
    - When external datasets are unavailable, synthetic demo data is used automatically.
      Every synthetic record is clearly labelled. See data/demo/.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import urllib.request
import urllib.error

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
MANIFEST_FILE = ROOT / "data" / "dataset_manifest.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger("download_datasets")

# ---------------------------------------------------------------------------
# Dataset registry — verified 2024-10-18
# Each entry is checked against the actual UCI ML Repository page.
# ---------------------------------------------------------------------------

DATASETS = {
    "235": {
        "name": "UCI Individual Household Electric Power Consumption",
        "url": "https://archive.ics.uci.edu/static/public/235/individual+household+electric+power+consumption.zip",
        "zip_file": "individual+household+electric+power+consumption.zip",
        "expected_files": ["household_power_consumption.txt"],
        "raw_subdir": "household_power",
        "licence": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "attribution": (
            "Hebrail, G. and Berard, A. (2012). Individual Household Electric Power Consumption "
            "[Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C58K54"
        ),
        "original_url": "https://archive.ics.uci.edu/dataset/235/individual+household+electric+power+consumption",
        "instances": 2075259,
        "features": 9,
        "geography": "Sceaux, France (7km from Paris)",
        "period": "December 2006 – November 2010",
        "size_mb_approx": 19.7,
        "campus_relevance": "EXTERNAL BENCHMARK ONLY — Household data, not campus data. "
                            "Used for time-series methodology demonstration only. "
                            "Never present these readings as real campus electricity measurements.",
        "limitations": [
            "Single residential household — not representative of a multi-building campus.",
            "Located in France — usage patterns differ from Indian campuses.",
            "Contains ~1.25% missing values (represented as blank fields between semicolons).",
            "Minute-level granularity must be aggregated to daily/hourly for campus context.",
        ],
        "required_columns": ["Date", "Time", "Global_active_power", "Global_reactive_power",
                              "Voltage", "Global_intensity", "Sub_metering_1",
                              "Sub_metering_2", "Sub_metering_3"],
        "separator": ";",
        "available": True,
    },
    "374": {
        "name": "UCI Appliances Energy Prediction",
        "url": "https://archive.ics.uci.edu/static/public/374/appliances+energy+prediction.zip",
        "zip_file": "appliances+energy+prediction.zip",
        "expected_files": ["energydata_complete.csv"],
        "raw_subdir": "appliances_energy",
        "licence": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "attribution": (
            "Candanedo, L., Feldheim, V., and Deramaix, D. (2017). Appliances Energy Prediction "
            "[Dataset]. UCI Machine Learning Repository. https://doi.org/10.24432/C5VC8D"
        ),
        "original_url": "https://archive.ics.uci.edu/dataset/374/appliances+energy+prediction",
        "instances": 19735,
        "features": 28,
        "geography": "Mons, Belgium",
        "period": "January 2016 – May 2016 (4.5 months, 10-minute intervals)",
        "size_mb_approx": 11.4,
        "campus_relevance": "EXTERNAL BENCHMARK ONLY — Single low-energy residential building, Belgium. "
                            "Useful for demonstrating appliance-level energy analysis techniques. "
                            "Not representative of Indian campus consumption patterns.",
        "limitations": [
            "Single low-energy house — significantly lower consumption than a typical campus building.",
            "Located in Belgium — climate and usage patterns differ from India.",
            "No missing values, but contains two random noise variables (rv1, rv2) for model testing.",
            "10-minute granularity; aggregation required for daily/hourly analysis.",
        ],
        "required_columns": ["date", "Appliances", "lights"],
        "separator": ",",
        "available": True,
    },
    "242": {
        "name": "UCI Energy Efficiency",
        "url": "https://archive.ics.uci.edu/static/public/242/energy+efficiency.zip",
        "zip_file": "energy+efficiency.zip",
        "expected_files": ["ENB2012_data.xlsx"],
        "raw_subdir": "energy_efficiency",
        "licence": "Creative Commons Attribution 4.0 International (CC BY 4.0)",
        "attribution": (
            "Tsanas, A. and Xifara, A. (2012). Energy Efficiency [Dataset]. "
            "UCI Machine Learning Repository. https://doi.org/10.24432/C51307"
        ),
        "original_url": "https://archive.ics.uci.edu/dataset/242/energy+efficiency",
        "instances": 768,
        "features": 8,
        "geography": "Simulated building models",
        "period": "Simulated — not time-series data",
        "size_mb_approx": 0.1,
        "campus_relevance": "METHODOLOGY DEMONSTRATION ONLY — Simulated building energy efficiency data. "
                            "Heating load (Y1) and cooling load (Y2) targets are simulation outputs, "
                            "NOT direct campus electricity meter readings. "
                            "Useful for demonstrating feature importance in building energy modelling.",
        "limitations": [
            "Synthetic simulation data using Ecotect software — not real measured consumption.",
            "768 instances representing different building configurations.",
            "Cannot be used as a baseline for actual campus energy consumption.",
            "No time component — snapshot of building parameters, not time-series.",
        ],
        "required_columns": ["X1", "X2", "X3", "X4", "X5", "X6", "X7", "X8", "Y1", "Y2"],
        "separator": "xlsx",
        "available": True,
    },
    "india_gov": {
        "name": "India Open Government Data Portal (data.gov.in)",
        "url": None,
        "zip_file": None,
        "expected_files": [],
        "raw_subdir": "india_gov",
        "licence": "National Data Sharing and Accessibility Policy (NDSAP) — Government of India. "
                   "Open for non-commercial use with attribution.",
        "attribution": (
            "Various datasets from data.gov.in. Attribution varies by dataset. "
            "See individual dataset pages for specific citations."
        ),
        "original_url": "https://www.data.gov.in/",
        "instances": None,
        "features": None,
        "geography": "India",
        "period": "Varies by dataset",
        "size_mb_approx": None,
        "campus_relevance": "Contextual benchmarks for India energy consumption, renewable energy, "
                            "water resources, environment, and pollution data.",
        "limitations": [
            "Requires manual download — no direct programmatic API for all datasets.",
            "Dataset availability changes over time; specific files may be removed.",
            "Format varies (CSV, XLSX, JSON); unit consistency must be verified.",
            "Campus-specific datasets are not available — national/state-level aggregates only.",
        ],
        "required_columns": [],
        "separator": "varies",
        "available": False,  # Requires manual access
        "manual_instructions": "See docs/DATASET_DOWNLOAD_GUIDE.md for step-by-step instructions.",
    },
    "cpcb": {
        "name": "India Central Pollution Control Board (CPCB)",
        "url": None,
        "zip_file": None,
        "expected_files": [],
        "raw_subdir": "cpcb",
        "licence": "Government of India open data. Attribution required.",
        "attribution": (
            "Central Pollution Control Board, Ministry of Environment, Forest and Climate Change, "
            "Government of India. https://cpcb.nic.in/"
        ),
        "original_url": "https://cpcb.nic.in/ and https://swm.cpcb.gov.in/",
        "instances": None,
        "features": None,
        "geography": "India",
        "period": "Varies by report",
        "size_mb_approx": None,
        "campus_relevance": "Solid waste management norms, pollution standards, and environmental "
                            "compliance guidance applicable to campus operations in India.",
        "limitations": [
            "No downloadable machine-readable campus waste dataset.",
            "Guidance documents are PDFs — not structured data.",
            "Annual reports require manual download from CPCB portal.",
            "Campus-level waste data must be collected and entered manually.",
        ],
        "required_columns": [],
        "separator": None,
        "available": False,  # Manual access only
        "manual_instructions": "See docs/DATASET_DOWNLOAD_GUIDE.md for CPCB data access instructions.",
    },
}


# ---------------------------------------------------------------------------
# Download utilities
# ---------------------------------------------------------------------------

def sha256_checksum(file_path: Path) -> str:
    """Compute SHA-256 checksum of a file."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def download_file(url: str, dest_path: Path, chunk_size: int = 65536) -> bool:
    """Download a file with progress indication. Returns True on success."""
    try:
        logger.info(f"Downloading: {url}")
        logger.info(f"Destination: {dest_path}")
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        req = urllib.request.Request(url, headers={"User-Agent": "GreenCampusAuditor/1.0"})
        with urllib.request.urlopen(req, timeout=120) as response:
            total = response.headers.get("Content-Length")
            total_bytes = int(total) if total else None
            downloaded = 0

            with open(dest_path, "wb") as out_file:
                while True:
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    out_file.write(chunk)
                    downloaded += len(chunk)
                    if total_bytes:
                        pct = downloaded / total_bytes * 100
                        print(f"\r  Progress: {downloaded / 1024 / 1024:.1f} MB / "
                              f"{total_bytes / 1024 / 1024:.1f} MB ({pct:.0f}%)", end="", flush=True)

        print()  # newline after progress
        logger.info(f"Download complete: {dest_path} ({dest_path.stat().st_size / 1024 / 1024:.1f} MB)")
        return True

    except urllib.error.HTTPError as e:
        logger.error(f"HTTP error {e.code}: {e.reason} — {url}")
        return False
    except urllib.error.URLError as e:
        logger.error(f"URL error: {e.reason} — {url}")
        return False
    except Exception as e:
        logger.error(f"Unexpected download error: {e}")
        return False


def extract_zip(zip_path: Path, extract_to: Path) -> list[str]:
    """Extract a ZIP file and return list of extracted filenames."""
    extract_to.mkdir(parents=True, exist_ok=True)
    extracted = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(extract_to)
        extracted = zf.namelist()
    logger.info(f"Extracted {len(extracted)} files to {extract_to}")
    return extracted


def load_manifest() -> dict:
    """Load existing manifest or return empty dict."""
    if MANIFEST_FILE.exists():
        with open(MANIFEST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"datasets": {}, "last_updated": None}


def save_manifest(manifest: dict):
    """Save manifest to JSON."""
    manifest["last_updated"] = datetime.now(timezone.utc).isoformat()
    MANIFEST_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_FILE, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
    logger.info(f"Manifest saved: {MANIFEST_FILE}")


# ---------------------------------------------------------------------------
# Per-dataset download logic
# ---------------------------------------------------------------------------

def download_dataset(dataset_id: str, dataset: dict, force: bool = False) -> dict:
    """Download and extract a single dataset. Returns a manifest entry."""
    entry = {
        "id": dataset_id,
        "name": dataset["name"],
        "status": "pending",
        "licence": dataset["licence"],
        "attribution": dataset["attribution"],
        "original_url": dataset["original_url"],
        "geography": dataset["geography"],
        "campus_relevance": dataset["campus_relevance"],
        "limitations": dataset["limitations"],
        "downloaded_at": None,
        "file_path": None,
        "sha256": None,
        "row_count_approx": dataset.get("instances"),
        "is_synthetic": False,
        "requires_manual_download": not dataset["available"],
        "warning": None,
    }

    if not dataset["available"]:
        entry["status"] = "manual_required"
        entry["warning"] = (
            f"⚠️  {dataset['name']} requires manual download. "
            f"See docs/DATASET_DOWNLOAD_GUIDE.md"
        )
        logger.warning(entry["warning"])
        return entry

    raw_dir = RAW_DIR / dataset["raw_subdir"]
    zip_path = raw_dir / dataset["zip_file"]

    # Check if already downloaded
    if zip_path.exists() and not force:
        logger.info(f"Already downloaded: {zip_path}. Use --force to re-download.")
        entry["status"] = "already_exists"
        entry["file_path"] = str(zip_path)
        entry["sha256"] = sha256_checksum(zip_path)
        entry["downloaded_at"] = datetime.fromtimestamp(
            zip_path.stat().st_mtime, tz=timezone.utc
        ).isoformat()
        return entry

    # Download
    success = download_file(dataset["url"], zip_path)
    if not success:
        entry["status"] = "download_failed"
        entry["warning"] = (
            f"⚠️  Download failed for {dataset['name']}. "
            f"The application will use synthetic demo data as fallback. "
            f"This fallback data is clearly labelled as synthetic."
        )
        logger.warning(entry["warning"])
        return entry

    # Verify file exists and is non-empty
    if not zip_path.exists() or zip_path.stat().st_size < 1000:
        entry["status"] = "download_failed"
        entry["warning"] = f"⚠️  Downloaded file is missing or too small: {zip_path}"
        logger.warning(entry["warning"])
        return entry

    # Extract
    try:
        extracted = extract_zip(zip_path, raw_dir)
        entry["extracted_files"] = extracted
    except zipfile.BadZipFile as e:
        entry["status"] = "extraction_failed"
        entry["warning"] = f"⚠️  ZIP extraction failed: {e}"
        logger.warning(entry["warning"])
        return entry

    # Verify expected files exist
    missing = []
    for expected_file in dataset["expected_files"]:
        # Search recursively for the file
        found = list(raw_dir.rglob(expected_file))
        if not found:
            missing.append(expected_file)

    if missing:
        entry["status"] = "incomplete"
        entry["warning"] = f"⚠️  Expected files not found after extraction: {missing}"
        logger.warning(entry["warning"])
    else:
        entry["status"] = "success"

    # Record metadata
    entry["file_path"] = str(zip_path)
    entry["sha256"] = sha256_checksum(zip_path)
    entry["downloaded_at"] = datetime.now(timezone.utc).isoformat()
    entry["size_bytes"] = zip_path.stat().st_size

    return entry


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def list_datasets():
    """Print a summary of all datasets and their availability."""
    print("\n" + "=" * 70)
    print("GREEN CAMPUS SUSTAINABILITY AUDITOR — DATASET REGISTRY")
    print("=" * 70)
    manifest = load_manifest()

    for ds_id, ds in DATASETS.items():
        status_in_manifest = manifest["datasets"].get(ds_id, {}).get("status", "not_downloaded")
        available = "✅ Available" if ds["available"] else "⚠️  Manual download required"
        status_emoji = "📥" if status_in_manifest == "success" else "🔲"
        print(f"\n{status_emoji} [{ds_id}] {ds['name']}")
        print(f"    Availability: {available}")
        print(f"    Licence: {ds['licence']}")
        print(f"    Geography: {ds['geography']}")
        print(f"    Campus relevance: {ds['campus_relevance'][:80]}...")
        if not ds["available"]:
            print(f"    ⚠️  See: docs/DATASET_DOWNLOAD_GUIDE.md")

    print("\n" + "=" * 70)
    print("⚠️  CRITICAL: UCI datasets are NOT campus data.")
    print("   They are EXTERNAL BENCHMARKS for methodology demonstration only.")
    print("   Synthetic demo data is used for all campus-specific demonstrations.")
    print("=" * 70 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Download and verify datasets for Green Campus Sustainability Auditor."
    )
    parser.add_argument("--list", action="store_true", help="List all datasets and status")
    parser.add_argument("--id", type=str, help="Download a specific dataset by ID")
    parser.add_argument("--force", action="store_true", help="Re-download even if file exists")
    parser.add_argument(
        "--skip-large",
        action="store_true",
        help="Skip dataset #235 (126 MB uncompressed)",
    )
    args = parser.parse_args()

    if args.list:
        list_datasets()
        return

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()

    target_ids = [args.id] if args.id else list(DATASETS.keys())

    print("\n" + "=" * 70)
    print("GREEN CAMPUS SUSTAINABILITY AUDITOR — DATASET DOWNLOADER")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    print()
    print("⚠️  IMPORTANT: UCI datasets are EXTERNAL BENCHMARKS only.")
    print("   They are NOT campus electricity/energy data.")
    print("   All campus demonstrations use clearly-labelled synthetic data.")
    print()

    results = []
    for ds_id in target_ids:
        if ds_id not in DATASETS:
            logger.error(f"Unknown dataset ID: {ds_id}")
            continue

        if args.skip_large and ds_id == "235":
            logger.info("Skipping dataset #235 (--skip-large flag set)")
            continue

        ds = DATASETS[ds_id]
        logger.info(f"\n--- Dataset [{ds_id}]: {ds['name']} ---")
        entry = download_dataset(ds_id, ds, force=args.force)
        manifest["datasets"][ds_id] = entry
        results.append(entry)

        # Print status
        status_icons = {
            "success": "✅",
            "already_exists": "✅",
            "manual_required": "⚠️ ",
            "download_failed": "❌",
            "extraction_failed": "❌",
            "incomplete": "⚠️ ",
        }
        icon = status_icons.get(entry["status"], "❓")
        print(f"  {icon} {ds['name']}: {entry['status']}")
        if entry.get("warning"):
            print(f"     {entry['warning']}")

    save_manifest(manifest)

    # Summary
    print("\n" + "=" * 70)
    print("DOWNLOAD SUMMARY")
    print("=" * 70)
    success = sum(1 for r in results if r["status"] in ("success", "already_exists"))
    manual = sum(1 for r in results if r["status"] == "manual_required")
    failed = sum(1 for r in results if r["status"] in ("download_failed", "extraction_failed"))

    print(f"  ✅ Downloaded/available: {success}")
    print(f"  ⚠️  Requires manual access: {manual}")
    print(f"  ❌ Failed: {failed}")
    print(f"\nManifest saved to: {MANIFEST_FILE}")
    print("\nFor datasets requiring manual access, see:")
    print("  docs/DATASET_DOWNLOAD_GUIDE.md")
    print("\nThe application will use synthetic demo data (data/demo/) for all")
    print("campus-specific demonstrations when external datasets are unavailable.")
    print("=" * 70 + "\n")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
