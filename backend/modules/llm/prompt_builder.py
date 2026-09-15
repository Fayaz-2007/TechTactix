"""
Builds a grounded, context-restricted prompt from retrieved chunks and the
user's query.
"""

SYSTEM_INSTRUCTION = (
    "You are a document assistant for confidential industrial documents. "
    "Answer the user's question using ONLY the information in the excerpts "
    "below. Do not use any outside knowledge. If the excerpts do not "
    "contain enough information to answer the question, respond exactly "
    "with: \"I don't have enough information.\" Be concise, and reference "
    "the excerpt number(s) you used when relevant. Answer only using the "
    "information in the excerpts above, in plain natural language. Never "
    "mention document IDs, chunk IDs, or internal identifiers — those are "
    "not part of the actual document content."
)


def build_prompt(query: str, retrieved_chunks: list) -> str:
    """
    Assemble a grounded prompt: system instruction, then labeled context
    chunks, then the user's query.

    Args:
        query: the user's natural-language question.
        retrieved_chunks: output of
            knowledge_base.vector_store.retrieve() — a list of
            {"chunk_text": str, "document_id": str, "chunk_id": str, "score": float}.
    """
    if retrieved_chunks:
        context_blocks = [
            f"Excerpt {i}:\n{chunk.get('chunk_text', '')}"
            for i, chunk in enumerate(retrieved_chunks, start=1)
        ]
        context_text = "\n\n".join(context_blocks)
    else:
        context_text = "(no relevant context was found)"

    return (
        f"{SYSTEM_INSTRUCTION}\n\n"
        f"### Context\n{context_text}\n\n"
        f"### Question\n{query}\n\n"
        f"### Answer\n"
    )
