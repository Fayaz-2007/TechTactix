"""
Standalone visual test for the report generators. Builds a DOCX and an
XLSX from hardcoded sample data and writes them to backend/data/, so they
can be opened and checked by eye.

Usage:
    python backend/modules/reports/test_reports.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.modules.reports.docx_generator import generate_docx  # noqa: E402
from backend.modules.reports.xlsx_generator import generate_xlsx  # noqa: E402

SAMPLE_QUERY = "What safety equipment is required on the factory floor?"

SAMPLE_ANSWER = (
    "Employees are required to wear safety goggles and steel-toed boots at "
    "all times while operating machinery on the factory floor. Pressure "
    "vessels must also be inspected annually by a certified engineer."
)

SAMPLE_SOURCES = [
    {
        "document_id": "doc-safety-manual",
        "chunk_id": "chunk-001",
        "chunk_text": (
            "All pressure vessels must be inspected annually by a certified "
            "engineer to verify structural integrity and detect corrosion."
        ),
        "score": 0.8123,
    },
    {
        "document_id": "doc-safety-manual",
        "chunk_id": "chunk-002",
        "chunk_text": (
            "Employees must wear safety goggles and steel-toed boots at all "
            "times while operating machinery on the factory floor."
        ),
        "score": 0.7554,
    },
]

OUTPUT_DIR = PROJECT_ROOT / "backend" / "data"


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    docx_bytes = generate_docx(SAMPLE_QUERY, SAMPLE_ANSWER, SAMPLE_SOURCES)
    docx_path = OUTPUT_DIR / "test_report.docx"
    docx_path.write_bytes(docx_bytes)
    print(f"Wrote {docx_path} ({len(docx_bytes)} bytes)")

    xlsx_bytes = generate_xlsx(SAMPLE_QUERY, SAMPLE_ANSWER, SAMPLE_SOURCES)
    xlsx_path = OUTPUT_DIR / "test_report.xlsx"
    xlsx_path.write_bytes(xlsx_bytes)
    print(f"Wrote {xlsx_path} ({len(xlsx_bytes)} bytes)")


if __name__ == "__main__":
    main()
