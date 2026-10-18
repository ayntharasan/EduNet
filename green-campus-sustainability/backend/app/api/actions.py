"""Action management endpoints."""
from datetime import date, datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.models.action import Action, ActionStatusHistory

router = APIRouter()

VALID_STATUSES = {"draft", "approved", "in-progress", "completed", "verified", "rejected"}


class ActionStatusUpdate(BaseModel):
    new_status: str
    changed_by: str = "user"
    notes: Optional[str] = None


class ActionDetail(BaseModel):
    id: int
    action_id: str
    run_id: str
    title: str
    description: str
    category: str
    cost_category: str
    implementation_difficulty: str
    time_horizon: str
    priority_score: float
    priority_rank: int
    priority_explanation: Optional[str]
    expected_impact: Optional[str]
    status: str
    assigned_to: Optional[str]
    target_date: Optional[date]
    completed_at: Optional[datetime]
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


@router.get("", response_model=list[ActionDetail])
def list_actions(
    run_id: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Action)
    if run_id:
        q = q.filter(Action.run_id == run_id)
    if status:
        q = q.filter(Action.status == status)
    return q.order_by(Action.priority_rank).all()


@router.get("/{action_id}", response_model=ActionDetail)
def get_action(action_id: str, db: Session = Depends(get_db)):
    a = db.query(Action).filter(Action.action_id == action_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Action not found.")
    return a


@router.patch("/{action_id}/status")
def update_action_status(
    action_id: str,
    payload: ActionStatusUpdate,
    db: Session = Depends(get_db),
):
    a = db.query(Action).filter(Action.action_id == action_id).first()
    if not a:
        raise HTTPException(status_code=404, detail="Action not found.")
    if payload.new_status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {sorted(VALID_STATUSES)}"
        )
    old_status = a.status
    a.status = payload.new_status
    if payload.new_status == "completed":
        a.completed_at = datetime.utcnow()
        a.completed_by = payload.changed_by

    db.add(ActionStatusHistory(
        action_id=action_id,
        old_status=old_status,
        new_status=payload.new_status,
        changed_by=payload.changed_by,
        notes=payload.notes,
    ))
    db.commit()
    return {"action_id": action_id, "old_status": old_status, "new_status": payload.new_status}


@router.get("/{action_id}/history")
def get_action_history(action_id: str, db: Session = Depends(get_db)):
    history = db.query(ActionStatusHistory).filter(
        ActionStatusHistory.action_id == action_id
    ).order_by(ActionStatusHistory.changed_at.asc()).all()
    return [
        {
            "old_status": h.old_status, "new_status": h.new_status,
            "changed_by": h.changed_by, "notes": h.notes,
            "changed_at": h.changed_at.isoformat(),
        }
        for h in history
    ]
