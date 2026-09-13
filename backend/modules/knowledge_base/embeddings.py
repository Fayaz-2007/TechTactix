"""
Wrapper around Ollama's local embeddings endpoint.

Fully offline: talks only to http://localhost:11434, which must already be
running with the "nomic-embed-text" model pulled
(`ollama pull nomic-embed-text`). No other network calls are made.
"""

import logging
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OLLAMA_BASE_URL = "http://localhost:11434"
EMBEDDINGS_ENDPOINT = f"{OLLAMA_BASE_URL}/api/embeddings"
EMBEDDING_MODEL = "nomic-embed-text"

REQUEST_TIMEOUT_SECONDS = 30
RETRY_DELAY_SECONDS = 1.5
MAX_ATTEMPTS = 2  # initial attempt + 1 retry


class EmbeddingError(Exception):
    """Raised when Ollama can't be reached or returns an unusable response."""


def _call_ollama_embeddings(text: str) -> list:
    response = requests.post(
        EMBEDDINGS_ENDPOINT,
        json={"model": EMBEDDING_MODEL, "prompt": text},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    embedding = data.get("embedding")
    if not embedding:
        raise EmbeddingError(f"Ollama returned no embedding for input (response: {data}).")
    return embedding


def embed_text(text: str) -> list:
    """
    Get an embedding vector for `text` from Ollama's local /api/embeddings
    endpoint using the nomic-embed-text model.

    Retries once on failure — Ollama can be slow or briefly unresponsive the
    first time it loads a model into memory.
    """
    if not text or not text.strip():
        raise EmbeddingError("Cannot embed empty text.")

    last_error: Optional[Exception] = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            return _call_ollama_embeddings(text)
        except Exception as exc:
            last_error = exc
            if attempt < MAX_ATTEMPTS:
                logger.warning(
                    "Ollama embeddings call failed (attempt %d/%d), retrying: %s",
                    attempt, MAX_ATTEMPTS, exc,
                )
                time.sleep(RETRY_DELAY_SECONDS)

    raise EmbeddingError(
        f"Failed to get embedding from Ollama at {EMBEDDINGS_ENDPOINT} "
        f"after {MAX_ATTEMPTS} attempts: {last_error}"
    ) from last_error
