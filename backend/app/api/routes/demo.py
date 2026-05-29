"""
Demo cases endpoint — returns pre-loaded patient data for quick testing.
"""

from fastapi import APIRouter, HTTPException
from app.core.mock_data import DEMO_CASES

router = APIRouter(prefix="/demo", tags=["demo"])


@router.get("/cases")
async def list_demo_cases():
    return [{"id": k, "label": v["label"]} for k, v in DEMO_CASES.items()]


@router.get("/cases/{case_id}")
async def get_demo_case(case_id: str):
    if case_id not in DEMO_CASES:
        raise HTTPException(status_code=404, detail=f"Demo case '{case_id}' not found.")
    return DEMO_CASES[case_id]["patient"]
