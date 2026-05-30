from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from app.core.database import get_db
from app.models.db.case import Case, CaseStatus
from app.models.db.user import User
from app.api.routes.auth import get_current_user

router = APIRouter(prefix="/cases", tags=["cases"])


class CaseCreate(BaseModel):
    title: str
    patient_data: dict
    clinical_notes: Optional[str] = None


class CaseSummary(BaseModel):
    id: str
    title: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime]
    patient_name: Optional[str]
    top_diagnosis: Optional[str]
    vcf_filename: Optional[str]

    class Config:
        from_attributes = True


@router.get("", response_model=List[CaseSummary])
def list_cases(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cases = (
        db.query(Case)
        .filter(Case.user_id == current_user.id)
        .order_by(Case.created_at.desc())
        .all()
    )
    result = []
    for c in cases:
        patient_name = None
        top_diagnosis = None
        if c.patient_data:
            fn = c.patient_data.get("first_name", "")
            ln = c.patient_data.get("last_name", "")
            patient_name = f"{fn} {ln}".strip() or None
        if c.result and isinstance(c.result, dict):
            deeprare = c.result.get("deeprare")
            if deeprare and isinstance(deeprare, dict):
                candidates = deeprare.get("candidates", [])
                if candidates:
                    top_diagnosis = candidates[0].get("disease_name")
        result.append(
            CaseSummary(
                id=c.id,
                title=c.title,
                status=c.status,
                created_at=c.created_at,
                completed_at=c.completed_at,
                patient_name=patient_name,
                top_diagnosis=top_diagnosis,
                vcf_filename=c.vcf_filename,
            )
        )
    return result


@router.post("", status_code=201)
def create_case(
    req: CaseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = Case(
        user_id=current_user.id,
        title=req.title,
        patient_data=req.patient_data,
        clinical_notes=req.clinical_notes,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return {
        "id": case.id,
        "title": case.title,
        "status": case.status,
        "created_at": case.created_at,
    }


@router.get("/{case_id}")
def get_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = (
        db.query(Case)
        .filter(Case.id == case_id, Case.user_id == current_user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    return {
        "id": case.id,
        "title": case.title,
        "status": case.status,
        "patient_data": case.patient_data,
        "result": case.result,
        "clinical_notes": case.clinical_notes,
        "vcf_filename": case.vcf_filename,
        "created_at": case.created_at,
        "completed_at": case.completed_at,
    }


@router.delete("/{case_id}", status_code=204)
def delete_case(
    case_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    case = (
        db.query(Case)
        .filter(Case.id == case_id, Case.user_id == current_user.id)
        .first()
    )
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    db.delete(case)
    db.commit()
