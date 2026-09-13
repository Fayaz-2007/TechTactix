"""
Thin wrapper around Ollama's local /api/generate endpoint for streaming
chat completions.

Fully offline: talks only to OLLAMA_BASE_URL (localhost). No other network
calls are made.
"""

import json
import logging
from typing import Generator

import requests

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)

GENERATE_ENDPOINT = f"{OLLAMA_BASE_URL}/api/generate"
REQUEST_TIMEOUT_SECONDS = 120  # CPU-only generation can legitimately take a while


class OllamaConnectionError(Exception):
    """Raised when Ollama can't be reached at all (e.g. not running)."""


class OllamaGenerationError(Exception):
    """Raised when Ollama responds but generation fails partway through."""


def stream_chat(prompt: str) -> Generator[str, None, None]:
    """
    Stream a chat completion for `prompt` from Ollama, yielding each text
    fragment (the "response" field of each NDJSON line) as it arrives.

    Raises:
        OllamaConnectionError: if Ollama isn't reachable at all.
        OllamaGenerationError: if the request fails or Ollama reports an
            error mid-stream.
    """
    try:
        response = requests.post(
            GENERATE_ENDPOINT,
            json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": True},
            stream=True,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError as exc:
        raise OllamaConnectionError(
            f"Could not connect to Ollama at {OLLAMA_BASE_URL}. Is it running?"
        ) from exc
    except requests.exceptions.RequestException as exc:
        raise OllamaGenerationError(f"Ollama request failed: {exc}") from exc

    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("Skipping unparseable line from Ollama: %r", line)
                continue

            if payload.get("error"):
                raise OllamaGenerationError(f"Ollama returned an error: {payload['error']}")

            fragment = payload.get("response", "")
            if fragment:
                yield fragment

            if payload.get("done"):
                break
    finally:
        response.close()
