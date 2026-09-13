"""
Standalone smoke test for the ingestion module (OCR + chunking only —
does not touch routes.py or the vector store, so it works before the rest
of the app is wired up).

Usage:
    python backend/modules/ingestion/test_ocr.py
    python backend/modules/ingestion/test_ocr.py path/to/file.pdf

With no argument, it picks the first PDF/PNG/JPG/JPEG file found under
backend/data/uploads/.
"""

import sys
from pathlib import Path

# Make `backend.*` importable when this file is run directly (not via -m).
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.ingestion.chunking import chunk_text  # noqa: E402
from backend.modules.ingestion.ocr import OCRError, SUPPORTED_EXTENSIONS, extract_text  # noqa: E402

UPLOADS_DIR = PROJECT_ROOT / "backend" / "data" / "uploads"


def find_sample_file() -> Path:
    if not UPLOADS_DIR.exists():
        raise FileNotFoundError(f"Uploads directory not found: {UPLOADS_DIR}")

    for path in sorted(UPLOADS_DIR.rglob("*")):
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return path

    raise FileNotFoundError(
        f"No sample PDF/PNG/JPG/JPEG file found under {UPLOADS_DIR}. "
        "Place a test file there, or pass a path as an argument."
    )


def main() -> None:
    if len(sys.argv) > 1:
        sample_path = Path(sys.argv[1]).resolve()
        if not sample_path.exists():
            print(f"File not found: {sample_path}")
            sys.exit(1)
    else:
        try:
            sample_path = find_sample_file()
        except FileNotFoundError as exc:
            print(str(exc))
            sys.exit(1)

    print(f"Running OCR on: {sample_path}")
    print("-" * 60)

    try:
        result = extract_text(str(sample_path), sample_path.name)
    except OCRError as exc:
        print(f"OCR FAILED: {exc}")
        sys.exit(1)

    full_text = result["full_text"]
    pages = result.get("pages", [])

    print(f"Pages/images processed: {len(pages)}")
    for page in pages:
        preview = page["text"][:200].replace("\n", " ")
        print(f"  - page {page['page_number']} [{page['method']}]: {len(page['text'])} chars | {preview!r}")

    print("-" * 60)
    print("FULL EXTRACTED TEXT:\n")
    print(full_text if full_text.strip() else "(no text extracted)")

    print("-" * 60)
    chunks = chunk_text(full_text)
    print(f"Chunk count: {len(chunks)}")
    for chunk in chunks:
        preview = chunk["text"][:120].replace("\n", " ")
        print(f"  [{chunk['order']}] id={chunk['chunk_id'][:8]} len={len(chunk['text'])} | {preview!r}")


if __name__ == "__main__":
    main()
