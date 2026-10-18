"""Buildings CRUD endpoints."""
from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from backend.app.database.session import get_db
from backend.app.models.building import Building

router = APIRouter()


class BuildingCreate(BaseModel):
    name: str
    building_type: str = "academic"
    floor_area_m2: Optional[float] = None
    student_capacity: Optional[int] = None
    staff_capacity: Optional[int] = None
    construction_year: Optional[int] = None
    notes: Optional[str] = None


class BuildingUpdate(BaseModel):
    name: Optional[str] = None
    building_type: Optional[str] = None
    floor_area_m2: Optional[float] = None
    student_capacity: Optional[int] = None
    staff_capacity: Optional[int] = None
    construction_year: Optional[int] = None
    notes: Optional[str] = None


class BuildingResponse(BaseModel):
    id: int
    name: str
    building_type: str
    floor_area_m2: Optional[float]
    student_capacity: Optional[int]
    staff_capacity: Optional[int]
    construction_year: Optional[int]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[BuildingResponse])
def list_buildings(db: Session = Depends(get_db)):
    return db.query(Building).all()


@router.post("", response_model=BuildingResponse, status_code=201)
def create_building(payload: BuildingCreate, db: Session = Depends(get_db)):
    existing = db.query(Building).filter(Building.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Building '{payload.name}' already exists.")
    b = Building(**payload.model_dump())
    db.add(b)
    db.commit()
    db.refresh(b)
    return b


@router.get("/{building_id}", response_model=BuildingResponse)
def get_building(building_id: int, db: Session = Depends(get_db)):
    b = db.query(Building).filter(Building.id == building_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Building not found.")
    return b


@router.put("/{building_id}", response_model=BuildingResponse)
def update_building(building_id: int, payload: BuildingUpdate, db: Session = Depends(get_db)):
    b = db.query(Building).filter(Building.id == building_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Building not found.")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(b, field, value)
    db.commit()
    db.refresh(b)
    return b


@router.delete("/{building_id}", status_code=204)
def delete_building(building_id: int, db: Session = Depends(get_db)):
    b = db.query(Building).filter(Building.id == building_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Building not found.")
    db.delete(b)
    db.commit()
    return None
