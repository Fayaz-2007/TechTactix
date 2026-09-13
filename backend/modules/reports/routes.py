"""
FastAPI route for generating downloadable DOCX/XLSX reports from a
query/answer/sources result. Pure local file generation — no network calls.
"""

import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.modules.reports.docx_generator import generate_docx
from backend.modules.reports.xlsx_generator import generate_xlsx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["reports"])

MEDIA_TYPES = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


class ReportRequest(BaseModel):
    query: str
    answer: str
    sources: list[dict] = Field(default_factory=list)
    format: str


@router.post("/generate-report")
async def generate_report(request: ReportRequest):
    fmt = request.format.lower().strip()
    if fmt not in MEDIA_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported format '{request.format}'. Use 'docx' or 'xlsx'.",
        )

    try:
        if fmt == "docx":
            file_bytes = generate_docx(request.query, request.answer, request.sources)
        else:
            file_bytes = generate_xlsx(request.query, request.answer, request.sources)
    except Exception as exc:
        logger.exception("Failed to generate %s report", fmt)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Could not generate {fmt} report.",
        ) from exc

    return Response(
        content=file_bytes,
        media_type=MEDIA_TYPES[fmt],
        headers={"Content-Disposition": f'attachment; filename="report.{fmt}"'},
    )
