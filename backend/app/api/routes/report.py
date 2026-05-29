"""
Report download endpoint.
In Phase 1 the report is generated on-the-fly from the submitted result payload.
Phase 2: cache generated reports by session_id.
"""

from fastapi import APIRouter
from fastapi.responses import Response
from pydantic import BaseModel

from app.models.pipeline import PipelineResult
from app.services.report_service import generate_pdf_report

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/generate")
async def generate_report(result: PipelineResult) -> Response:
    pdf_bytes = generate_pdf_report(result)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="raredx-{result.session_id}.pdf"'
        },
    )
