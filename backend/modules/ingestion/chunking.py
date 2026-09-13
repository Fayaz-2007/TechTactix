"""
Splits extracted document text into overlapping, sentence-boundary-aware
chunks for downstream embedding/indexing.

No tokenizer dependency is used (keeps the module fully offline with no
model/vocab downloads) — token counts are approximated from word counts,
which is accurate enough for sizing chunks in a RAG pipeline.
"""

import re
import uuid

# Splits on sentence-ending punctuation followed by whitespace + the start
# of a new sentence, or on blank-line paragraph breaks.
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])|\n\s*\n+")

# Average English tokens per whitespace-delimited word (tokens tend to be
# shorter than whole words), used to approximate token counts.
_TOKENS_PER_WORD = 1.3


def split_into_sentences(text: str) -> list:
    """Split text into a list of non-empty sentence/paragraph-ish strings."""
    text = (text or "").strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def _estimate_tokens(text: str) -> int:
    word_count = len(text.split())
    return max(1, round(word_count * _TOKENS_PER_WORD))


def _split_long_text_by_words(text: str, max_tokens: int) -> list:
    """Break a single very long sentence into word-based pieces near max_tokens."""
    words = text.split()
    if not words:
        return []

    pieces = []
    current: list = []
    current_tokens = 0
    for word in words:
        word_tokens = _estimate_tokens(word)
        if current and current_tokens + word_tokens > max_tokens:
            pieces.append(" ".join(current))
            current = []
            current_tokens = 0
        current.append(word)
        current_tokens += word_tokens
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_text(text: str, target_tokens: int = 500, overlap_tokens: int = 50) -> list:
    """
    Split text into overlapping chunks, trying not to cut sentences mid-way.

    Args:
        text: The full extracted document text.
        target_tokens: Approximate token budget per chunk (default ~500).
        overlap_tokens: Approximate tokens of trailing context carried over
            into the next chunk (default ~50).

    Returns:
        A list of {"chunk_id": str, "text": str, "order": int}, ordered
        from start to end of the document.
    """
    sentences = split_into_sentences(text)
    if not sentences:
        return []

    chunks: list = []
    buffer: list = []
    buffer_tokens = 0
    order = 0

    def emit(chunk_value: str) -> None:
        nonlocal order
        chunk_value = chunk_value.strip()
        if not chunk_value:
            return
        chunks.append({"chunk_id": str(uuid.uuid4()), "text": chunk_value, "order": order})
        order += 1

    def flush_buffer() -> None:
        """Emit the buffer as a chunk, then seed the buffer with trailing overlap."""
        nonlocal buffer, buffer_tokens
        if not buffer:
            return
        emit(" ".join(buffer))

        overlap: list = []
        overlap_tokens_count = 0
        for sentence in reversed(buffer):
            s_tokens = _estimate_tokens(sentence)
            if overlap_tokens_count + s_tokens > overlap_tokens:
                break
            overlap.insert(0, sentence)
            overlap_tokens_count += s_tokens

        buffer = overlap
        buffer_tokens = overlap_tokens_count

    for sentence in sentences:
        sentence_tokens = _estimate_tokens(sentence)

        # A single sentence bigger than the whole target budget (e.g. OCR
        # noise with no punctuation): flush what we have, then hard-split
        # this sentence on word boundaries instead of emitting one huge chunk.
        if sentence_tokens > target_tokens:
            flush_buffer()
            buffer = []
            buffer_tokens = 0
            for piece in _split_long_text_by_words(sentence, target_tokens):
                emit(piece)
            continue

        if buffer and buffer_tokens + sentence_tokens > target_tokens:
            flush_buffer()

        buffer.append(sentence)
        buffer_tokens += sentence_tokens

    flush_buffer()
    return chunks
