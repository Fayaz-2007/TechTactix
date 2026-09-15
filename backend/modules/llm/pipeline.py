"""
End-to-end RAG query pipeline: retrieve relevant chunks, build a grounded
prompt, and stream the model's answer, followed by a final sources payload.
"""

import logging
from typing import Generator, Optional

from backend.modules.knowledge_base.vector_store import retrieve
from backend.modules.llm.ollama_client import stream_chat
from backend.modules.llm.prompt_builder import build_prompt

logger = logging.getLogger(__name__)


def _dedupe_sources(chunks: list) -> list:
    """
    Collapse retrieved chunks into one source entry per file, so a file
    matched by several chunks shows up once in the response instead of once
    per chunk.

    Chunks are grouped by filename; a chunk with no filename falls back to
    grouping by document_id, same as the display fallback in the frontend.
    Within a group, the highest-scoring chunk wins (its document_id/chunk_id/
    score are what's kept) — not an average, not the first one seen. The
    result is sorted by score, highest first.
    """
    best_by_key: dict = {}
    for chunk in chunks:
        key = chunk.get("filename") or chunk.get("document_id")
        score = chunk.get("score") or 0
        existing = best_by_key.get(key)
        if existing is None or score > (existing.get("score") or 0):
            best_by_key[key] = {
                "document_id": chunk.get("document_id"),
                "chunk_id": chunk.get("chunk_id"),
                "filename": chunk.get("filename"),
                "score": chunk.get("score"),
            }
    return sorted(best_by_key.values(), key=lambda s: s.get("score") or 0, reverse=True)


def _describe_retrieval(chunks: list) -> str:
    """Build a human-readable status line from the actual retrieval result."""
    if not chunks:
        return "No relevant sections found in the indexed documents."

    filenames = []
    for chunk in chunks:
        name = chunk.get("filename") or chunk.get("document_id")
        if name and name not in filenames:
            filenames.append(name)

    count = len(chunks)
    noun = "section" if count == 1 else "sections"
    return f"Found {count} relevant {noun} from {', '.join(filenames)}"


def run_query(query: str, document_id: Optional[str] = None, project_id: Optional[str] = None) -> Generator:
    """
    Run the retrieve -> build_prompt -> stream_chat pipeline for `query`.

    Args:
        query: the user's natural-language question.
        document_id: restrict retrieval to one document, if given.
        project_id: restrict retrieval to one project's documents, if given.
            Combines with document_id when both are given; omitted, search
            covers every indexed document as before projects existed.

    Yields:
        dict: {"type": "status", "message": str} — real-time pipeline state,
            built from the actual retrieval result (chunk count, source
            filenames), not placeholder text.
        str: each streamed text fragment from the model, in order.
        dict: exactly one final item, after all text fragments:
            {"type": "done", "sources": [{"document_id": str, "chunk_id": str, "filename": str, "score": float}, ...]}
            One entry per file (deduped by filename, or document_id when
            filename is missing), keeping each file's highest-scoring chunk,
            sorted by score descending.

    Any exception raised by retrieval or generation (e.g. Ollama being
    unreachable) propagates to the caller — this function does not swallow
    errors, so the route layer can turn them into a clear SSE error event.
    """
    yield {"type": "status", "message": "Searching indexed documents..."}

    retrieved_chunks = retrieve(query, document_id=document_id, project_id=project_id)

    yield {"type": "status", "message": _describe_retrieval(retrieved_chunks)}

    prompt = build_prompt(query, retrieved_chunks)

    yield {"type": "status", "message": "Generating answer..."}

    for fragment in stream_chat(prompt):
        yield fragment

    sources = _dedupe_sources(retrieved_chunks)
    yield {"type": "done", "sources": sources}
