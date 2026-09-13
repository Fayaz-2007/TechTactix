"""
FastAPI route for the RAG chat pipeline, streamed to the client over
Server-Sent Events (SSE) — one-way server-to-client streaming, no
WebSocket needed.
"""

import json
import logging
import uuid
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from backend.modules.history.db import add_message, create_session
from backend.modules.llm.ollama_client import OllamaConnectionError, OllamaGenerationError
from backend.modules.llm.pipeline import run_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

TITLE_PREVIEW_LENGTH = 40


class ChatRequest(BaseModel):
    query: str
    document_id: Optional[str] = None
    session_id: Optional[str] = None
    project_id: Optional[str] = None


def _sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _make_title(query: str) -> str:
    title = query.strip().replace("\n", " ")[:TITLE_PREVIEW_LENGTH]
    return title or "New chat"


def _stream_chat_response(query: str, document_id: Optional[str], session_id: str, project_id: Optional[str]):
    full_answer = ""
    try:
        for item in run_query(query, document_id=document_id, project_id=project_id):
            if isinstance(item, str):
                full_answer += item
                yield _sse_event({"type": "token", "token": item})
            elif item.get("type") == "status":
                yield _sse_event(item)
            elif item.get("type") == "done":
                sources = item.get("sources", [])
                add_message(session_id, "assistant", full_answer, sources)
                yield _sse_event({"type": "done", "sources": sources, "session_id": session_id})
    except OllamaConnectionError as exc:
        logger.error("Ollama unreachable: %s", exc)
        yield _sse_event({"error": str(exc)})
    except OllamaGenerationError as exc:
        logger.error("Ollama generation error: %s", exc)
        yield _sse_event({"error": str(exc)})
    except Exception as exc:
        logger.exception("Unexpected error in chat pipeline")
        yield _sse_event({"error": f"Unexpected error: {exc}"})


@router.post("/chat")
async def chat(request: ChatRequest):
    session_id = request.session_id
    if not session_id:
        session_id = str(uuid.uuid4())
        create_session(session_id, _make_title(request.query), project_id=request.project_id)

    add_message(session_id, "user", request.query)

    return StreamingResponse(
        _stream_chat_response(request.query, request.document_id, session_id, request.project_id),
        media_type="text/event-stream",
    )
