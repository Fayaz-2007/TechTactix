"""
Standalone smoke test for the LLM module's RAG pipeline.

Mocks knowledge_base.vector_store.retrieve() with two fake sample chunks so
this runs even before the knowledge base module is wired in for real — only
Ollama (for chat generation) needs to be running locally with
OLLAMA_MODEL (see backend/config.py) pulled.

Usage:
    python backend/modules/llm/test_pipeline.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import backend.modules.llm.pipeline as pipeline_module  # noqa: E402
from backend.modules.llm.ollama_client import OllamaConnectionError, OllamaGenerationError  # noqa: E402

FAKE_CHUNKS = [
    {
        "chunk_text": (
            "All pressure vessels must be inspected annually by a certified "
            "engineer to verify structural integrity and detect corrosion."
        ),
        "document_id": "doc-safety-manual",
        "chunk_id": "chunk-001",
        "score": 0.81,
    },
    {
        "chunk_text": (
            "Employees must wear safety goggles and steel-toed boots at all "
            "times while operating machinery on the factory floor."
        ),
        "document_id": "doc-safety-manual",
        "chunk_id": "chunk-002",
        "score": 0.76,
    },
]


def fake_retrieve(query: str, top_k: int = 4, document_id=None) -> list:
    return FAKE_CHUNKS


SAMPLE_QUERY = "What safety equipment is required on the factory floor?"


def main() -> None:
    # Patch the name inside the pipeline module (it already imported its own
    # reference to `retrieve`, so patching the original module wouldn't reach it).
    pipeline_module.retrieve = fake_retrieve

    print(f"Query: {SAMPLE_QUERY!r}")
    print("-" * 60)

    try:
        for item in pipeline_module.run_query(SAMPLE_QUERY, document_id=None):
            if isinstance(item, str):
                print(item, end="", flush=True)
            else:
                print("\n" + "-" * 60)
                print("Sources used:")
                for source in item.get("sources", []):
                    print(f"  - {source}")
    except OllamaConnectionError as exc:
        print(f"\nPIPELINE FAILED (is Ollama running?): {exc}")
        sys.exit(1)
    except OllamaGenerationError as exc:
        print(f"\nPIPELINE FAILED: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
