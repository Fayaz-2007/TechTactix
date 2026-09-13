"""
Persistent Chroma vector store for indexed document chunks.

Fully offline: chromadb runs embedded (no separate server process),
persisting to backend/data/chroma_db/ so indexed documents survive a
server restart. Embeddings come from Ollama via
backend.modules.knowledge_base.embeddings.embed_text.
"""

import logging
from pathlib import Path
from typing import Optional

import chromadb

from backend.modules.knowledge_base.embeddings import embed_text

logger = logging.getLogger(__name__)

# backend/modules/knowledge_base/vector_store.py -> parents[2] == backend/
CHROMA_PERSIST_DIR = Path(__file__).resolve().parents[2] / "data" / "chroma_db"
CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

COLLECTION_NAME = "document_chunks"

_client = chromadb.PersistentClient(path=str(CHROMA_PERSIST_DIR))
_collection = _client.get_or_create_collection(
    name=COLLECTION_NAME,
    metadata={"hnsw:space": "cosine"},
)


def index_chunks(
    document_id: str,
    chunks: list,
    filename: Optional[str] = None,
    project_id: Optional[str] = None,
) -> None:
    """
    Embed each chunk's text and store it in Chroma.

    Called by the ingestion module right after OCR + chunking — this exact
    signature is relied on by backend/modules/ingestion/routes.py.

    Args:
        document_id: id of the parent document.
        chunks: list of {"chunk_id": str, "text": str, "order": int}.
        filename: original uploaded filename, stored alongside each chunk so
            retrieval results can show a human-readable source instead of
            just the document_id UUID.
        project_id: optional project this document belongs to. A document
            with no project_id is unscoped — it's included in every
            project-unfiltered search, same as before projects existed.
    """
    if not chunks:
        return

    ids = []
    embeddings = []
    documents = []
    metadatas = []

    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        text = chunk["text"]
        order = chunk["order"]

        embedding = embed_text(text)

        ids.append(chunk_id)
        embeddings.append(embedding)
        documents.append(text)
        metadatas.append({
            "document_id": document_id,
            "chunk_id": chunk_id,
            "order": order,
            # Chroma metadata values can't be None, so fall back to "".
            "filename": filename or "",
            "project_id": project_id or "",
        })

    _collection.add(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )
    logger.info("Indexed %d chunks for document %s", len(ids), document_id)


def retrieve(
    query: str,
    top_k: int = 4,
    document_id: Optional[str] = None,
    project_id: Optional[str] = None,
) -> list:
    """
    Embed `query` and return the top_k most similar chunks.

    Args:
        query: natural-language query text.
        top_k: max number of matches to return.
        document_id: if given, restrict the search to chunks from this
            document only.
        project_id: if given, restrict the search to chunks from documents
            tagged with this project. Combines with document_id when both
            are given. Omitted (None), search covers every document as before
            projects existed.

    Returns:
        A list of, ordered most to least relevant:
            {"chunk_text": str, "document_id": str, "chunk_id": str, "score": float}
        `score` is a cosine-similarity value (1 - cosine distance); higher
        means more relevant.
    """
    if _collection.count() == 0:
        return []

    query_embedding = embed_text(query)

    conditions = []
    if document_id:
        conditions.append({"document_id": document_id})
    if project_id:
        conditions.append({"project_id": project_id})

    if not conditions:
        where = None
    elif len(conditions) == 1:
        where = conditions[0]
    else:
        where = {"$and": conditions}

    results = _collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )

    result_ids = results.get("ids", [[]])[0]
    result_documents = results.get("documents", [[]])[0]
    result_metadatas = results.get("metadatas", [[]])[0]
    result_distances = results.get("distances", [[]])[0]

    matches = []
    for chunk_id, text, metadata, distance in zip(
        result_ids, result_documents, result_metadatas, result_distances
    ):
        matches.append({
            "chunk_text": text,
            "document_id": metadata.get("document_id"),
            "chunk_id": metadata.get("chunk_id", chunk_id),
            "filename": metadata.get("filename") or None,
            "score": 1.0 - distance,
        })
    return matches


def list_documents(project_id: Optional[str] = None) -> list:
    """
    Return [{"document_id", "filename", "project_id", "chunk_count"}, ...]
    for every indexed document, optionally restricted to one project. Used
    by GET /api/documents and GET /api/projects/{id}/documents.
    """
    if _collection.count() == 0:
        return []

    all_metadatas = _collection.get(include=["metadatas"])["metadatas"]

    documents: dict = {}
    for metadata in all_metadatas:
        doc_id = metadata.get("document_id")
        if doc_id is None:
            continue

        doc_project_id = metadata.get("project_id") or None
        if project_id and doc_project_id != project_id:
            continue

        if doc_id not in documents:
            documents[doc_id] = {
                "document_id": doc_id,
                "filename": metadata.get("filename") or None,
                "project_id": doc_project_id,
                "chunk_count": 0,
            }
        documents[doc_id]["chunk_count"] += 1

    return list(documents.values())
