"""Dataset upload and listing endpoints."""
import hashlib
import io
import datetime as dt
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.database.session import get_db
from backend.app.models.dataset_source import DatasetSource
from backend.app.models.electricity import ElectricityMeasurement
from backend.app.models.water import WaterMeasurement
from backend.app.models.waste import WasteMeasurement

router = APIRouter()

MAX_SIZE_BYTES = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
UPLOAD_DIR = Path(settings.UPLOAD_DIR)
ALLOWED_EXTENSIONS = {".csv", ".xlsx", ".xls"}


class DatasetResponse(BaseModel):
    id: int
    name: str
    source_type: str
    filename: Optional[str]
    licence: Optional[str]
    attribution: Optional[str]
    row_count: Optional[int]
    is_synthetic: bool
    notes: Optional[str]
    imported_at: dt.datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[DatasetResponse])
def list_datasets(db: Session = Depends(get_db)):
    return db.query(DatasetSource).order_by(DatasetSource.imported_at.desc()).all()


@router.get("/{dataset_id}", response_model=DatasetResponse)
def get_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.query(DatasetSource).filter(DatasetSource.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    return ds


@router.post("/upload/{data_type}", status_code=201)
async def upload_dataset(
    data_type: str,
    file: UploadFile = File(...),
    name: str = Form(...),
    licence: str = Form(default=""),
    attribution: str = Form(default=""),
    notes: str = Form(default=""),
    db: Session = Depends(get_db),
):
    """Upload a CSV or Excel file and import rows into the database.

    data_type must be one of: electricity, water, waste
    """
    if data_type not in ("electricity", "water", "waste"):
        raise HTTPException(status_code=400, detail="data_type must be electricity, water, or waste.")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail=f"File type {suffix} not supported. Use CSV or Excel.")

    content = await file.read()
    if len(content) > MAX_SIZE_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {settings.MAX_UPLOAD_SIZE_MB} MB limit.")

    # Save with a hashed filename to prevent path traversal
    checksum = hashlib.sha256(content).hexdigest()[:16]
    safe_name = f"{checksum}_{Path(file.filename).name}"
    UPLOAD_DIR.mkdir(exist_ok=True)
    dest_path = UPLOAD_DIR / safe_name
    with open(dest_path, "wb") as f_out:
        f_out.write(content)

    try:
        if suffix == ".csv":
            df = pd.read_csv(io.BytesIO(content))
        else:
            df = pd.read_excel(io.BytesIO(content))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Could not parse file: {e}")

    ds = DatasetSource(
        name=name,
        source_type="upload",
        filename=file.filename,
        file_path=str(dest_path),
        licence=licence or None,
        attribution=attribution or None,
        row_count=len(df),
        is_synthetic=False,
        notes=notes or None,
    )
    db.add(ds)
    db.flush()

    imported, errors = _import_rows(df, data_type, ds.id, db)
    db.commit()

    return {
        "dataset_id": ds.id,
        "filename": file.filename,
        "rows_parsed": len(df),
        "rows_imported": imported,
        "errors": errors[:20],
        "file_saved": str(dest_path),
    }


def _import_rows(df: pd.DataFrame, data_type: str, dataset_source_id: int, db: Session) -> tuple[int, list[str]]:
    """Parse DataFrame and insert into the measurements table. Returns (imported, errors)."""
    imported = 0
    errors = []
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    for idx, row in df.iterrows():
        try:
            if data_type == "electricity":
                ts = _parse_date(row, ["timestamp", "date", "measurement_date"])
                if ts is None:
                    errors.append(f"Row {idx}: missing timestamp/date.")
                    continue
                kwh = _parse_float(row, ["consumption_kwh", "kwh", "energy_kwh"])
                if kwh is None or kwh < 0:
                    errors.append(f"Row {idx}: missing or negative consumption_kwh.")
                    continue
                bid = _parse_int(row, ["building_id"]) or 1
                rec = ElectricityMeasurement(
                    timestamp=ts, building_id=bid, consumption_kwh=kwh,
                    occupancy_count=_parse_int(row, ["occupancy_count", "occupancy"]),
                    floor_area_m2=_parse_float(row, ["floor_area_m2", "area_m2"]),
                    source_type="upload", is_synthetic=False, dataset_source_id=dataset_source_id,
                )
                db.add(rec)

            elif data_type == "water":
                ts = _parse_date(row, ["measurement_date", "date", "timestamp"])
                if ts is None:
                    errors.append(f"Row {idx}: missing date.")
                    continue
                litres = _parse_float(row, ["consumption_litres", "litres", "water_litres"])
                if litres is None or litres < 0:
                    errors.append(f"Row {idx}: missing or negative consumption_litres.")
                    continue
                bid = _parse_int(row, ["building_id"]) or 1
                rec = WaterMeasurement(
                    measurement_date=ts, building_id=bid, consumption_litres=litres,
                    occupancy_count=_parse_int(row, ["occupancy_count"]),
                    source_type="upload", is_synthetic=False, dataset_source_id=dataset_source_id,
                )
                db.add(rec)

            elif data_type == "waste":
                ts = _parse_date(row, ["measurement_date", "date", "timestamp"])
                if ts is None:
                    errors.append(f"Row {idx}: missing date.")
                    continue
                total = _parse_float(row, ["total_waste_kg", "total_kg", "waste_kg"])
                if total is None or total < 0:
                    errors.append(f"Row {idx}: missing or negative total_waste_kg.")
                    continue
                bid = _parse_int(row, ["building_id"]) or 1
                rec = WasteMeasurement(
                    measurement_date=ts, building_id=bid,
                    wet_waste_kg=_parse_float(row, ["wet_waste_kg", "wet_kg"]) or 0.0,
                    dry_recyclable_kg=_parse_float(row, ["dry_recyclable_kg", "dry_kg", "recyclable_kg"]) or 0.0,
                    residual_waste_kg=_parse_float(row, ["residual_waste_kg", "residual_kg"]) or 0.0,
                    special_waste_kg=_parse_float(row, ["special_waste_kg", "special_kg"]) or 0.0,
                    total_waste_kg=total, source_type="upload", is_synthetic=False, dataset_source_id=dataset_source_id,
                )
                db.add(rec)

            imported += 1
        except Exception as e:
            errors.append(f"Row {idx}: {e}")

    return imported, errors


def _parse_date(row, keys: list[str]):
    for k in keys:
        if k in row and pd.notna(row[k]):
            try:
                val = row[k]
                if isinstance(val, dt.date):
                    return val
                return pd.to_datetime(val).date()
            except Exception:
                continue
    return None


def _parse_float(row, keys: list[str]) -> float | None:
    for k in keys:
        if k in row and pd.notna(row[k]):
            try:
                return float(row[k])
            except (TypeError, ValueError):
                continue
    return None


def _parse_int(row, keys: list[str]) -> int | None:
    for k in keys:
        if k in row and pd.notna(row[k]):
            try:
                return int(row[k])
            except (TypeError, ValueError):
                continue
    return None


@router.delete("/{dataset_id}", status_code=204)
def delete_dataset(dataset_id: int, db: Session = Depends(get_db)):
    ds = db.query(DatasetSource).filter(DatasetSource.id == dataset_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found.")
    db.delete(ds)
    db.commit()
    return None
