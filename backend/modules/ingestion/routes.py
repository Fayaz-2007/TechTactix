"""
FastAPI routes for document ingestion: upload -> OCR -> chunk -> index.

Fully offline. Any failure to read/decode an uploaded file (corrupt PDF,
truncated image, unsupported format, oversized file, etc.) is caught per
file and reported in that file's own result entry instead of failing the
whole batch or crashing the server.
"""

import logging
import shutil
import uuid
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from backend.modules.ingestion.chunking import chunk_text
from backend.modules.ingestion.ocr import OCRError, SUPPORTED_EXTENSIONS, extract_text
from backend.modules.knowledge_base.vector_store import index_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["ingestion"])

# backend/modules/ingestion/routes.py -> parents[2] == backend/
UPLOAD_ROOT = Path(__file__).resolve().parents[2] / "data" / "uploads"

MAX_FILES_PER_UPLOAD = 5
MAX_UPLOAD_SIZE_BYTES = 15 * 1024 * 1024  # 15 MB per file


async def _process_single_upload(file: UploadFile, project_id: Optional[str]) -> dict:
    """Save, extract, chunk, and index one file. Never raises — failures are
    reported back as a {"status": "error", ...} entry instead."""
    original_filename = file.filename or "upload"
    extension = Path(original_filename).suffix.lower()

    def error_result(message: str) -> dict:
        return {
            "document_id": None,
            "filename": original_filename,
            "chunks_indexed": 0,
            "status": "error",
            "error": message,
        }

    if extension not in SUPPORTED_EXTENSIONS:
        return error_result(
            f"Unsupported file type '{extension}'. "
            f"Allowed: {', '.join(sorted(SUPPORTED_EXTENSIONS))}."
        )

    document_id = str(uuid.uuid4())
    document_dir = UPLOAD_ROOT / document_id
    document_dir.mkdir(parents=True, exist_ok=True)
    saved_path = document_dir / original_filename

    # --- Save raw upload ---
    try:
        contents = await file.read()
        if not contents:
            raise ValueError("Uploaded file is empty.")
        if len(contents) > MAX_UPLOAD_SIZE_BYTES:
            raise ValueError("File exceeds 15MB limit")

        with open(saved_path, "wb") as out_file:
            out_file.write(contents)
    except ValueError as exc:
        shutil.rmtree(document_dir, ignore_errors=True)
        return error_result(str(exc))
    except Exception:
        shutil.rmtree(document_dir, ignore_errors=True)
        logger.exception("Failed to save uploaded file %s", original_filename)
        return error_result("Could not save the uploaded file.")
    finally:
        await file.close()

    # --- Extract text (PDF / image OCR / Excel dispatch) ---
    try:
        extraction_result = extract_text(str(saved_path), original_filename)
    except OCRError as exc:
        shutil.rmtree(document_dir, ignore_errors=True)
        return error_result(str(exc))
    except Exception:
        shutil.rmtree(document_dir, ignore_errors=True)
        logger.exception("Unexpected error extracting text from %s", original_filename)
        return error_result(
            "Could not extract text from the uploaded file. It may be corrupt or unreadable."
        )

    full_text = extraction_result.get("full_text", "")
    if not full_text.strip():
        shutil.rmtree(document_dir, ignore_errors=True)
        return error_result("No readable text could be extracted from this file.")

    # --- Chunk ---
    chunks = chunk_text(full_text)

    # --- Index (implemented in backend/modules/knowledge_base/vector_store.py) ---
    try:
        index_chunks(document_id, chunks, filename=original_filename, project_id=project_id)
    except Exception:
        logger.exception("Failed to index chunks for document %s", document_id)
        return error_result("Document was processed but could not be indexed.")

    return {
        "document_id": document_id,
        "filename": original_filename,
        "chunks_indexed": len(chunks),
        "status": "success",
        "error": None,
    }


@router.post("/upload")
async def upload_document(
    files: List[UploadFile] = File(...), project_id: Optional[str] = Form(None)
):
    if len(files) > MAX_FILES_PER_UPLOAD:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload up to 5 files at a time",
        )

    results = []
    for file in files:
        results.append(await _process_single_upload(file, project_id))
    return results
