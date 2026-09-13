"""
Standalone smoke test for the knowledge base module (Ollama embeddings +
persistent Chroma vector store). Indexes a few inline sample chunks under a
fresh, disposable document_id and runs a sample query against them, so
retrieval quality can be checked before this is wired into the chat
pipeline.

Requires Ollama running locally with "nomic-embed-text" pulled:
    ollama pull nomic-embed-text

Usage:
    python backend/modules/knowledge_base/test_retrieval.py
"""

import sys
import uuid
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.knowledge_base.embeddings import EmbeddingError  # noqa: E402
from backend.modules.knowledge_base.vector_store import index_chunks, retrieve  # noqa: E402

SAMPLE_TEXTS = [
    "All pressure vessels must be inspected annually by a certified engineer "
    "to verify structural integrity and detect corrosion.",
    "Employees must wear safety goggles and steel-toed boots at all times "
    "while operating machinery on the factory floor.",
    "The quarterly financial report shows a 12% increase in revenue, driven "
    "mainly by new export contracts signed in Q2.",
]

SAMPLE_QUERY = "What safety equipment is required on the factory floor?"


def build_sample_chunks() -> list:
    return [
        {"chunk_id": str(uuid.uuid4()), "text": text, "order": i}
        for i, text in enumerate(SAMPLE_TEXTS)
    ]


def main() -> None:
    document_id = f"test-doc-{uuid.uuid4().hex[:8]}"
    chunks = build_sample_chunks()

    print(f"Indexing {len(chunks)} sample chunks under document_id={document_id} ...")
    try:
        index_chunks(document_id, chunks)
    except EmbeddingError as exc:
        print(f"INDEXING FAILED (is Ollama running with nomic-embed-text pulled?): {exc}")
        sys.exit(1)
    print("Indexed.\n")

    print(f"Query: {SAMPLE_QUERY!r}")
    print("-" * 60)
    try:
        results = retrieve(SAMPLE_QUERY, top_k=3, document_id=document_id)
    except EmbeddingError as exc:
        print(f"RETRIEVAL FAILED: {exc}")
        sys.exit(1)

    if not results:
        print("No results returned.")
        return

    for rank, result in enumerate(results, start=1):
        print(f"[{rank}] score={result['score']:.4f}  chunk_id={result['chunk_id'][:8]}")
        print(f"    {result['chunk_text']}")
        print()


if __name__ == "__main__":
    main()
