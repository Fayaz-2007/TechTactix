"""
FastAPI routes for the knowledge base: checking what's been indexed so far.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from backend.modules.knowledge_base.vector_store import list_documents

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["knowledge_base"])


@router.get("/documents")
async def get_documents():
    """List every indexed document_id along with how many chunks it has."""
    try:
        documents = list_documents()
    except Exception as exc:
        logger.exception("Failed to list indexed documents")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not list indexed documents.",
        ) from exc

    return {"documents": documents, "total_documents": len(documents)}
