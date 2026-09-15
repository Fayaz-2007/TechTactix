"""
Text extraction for the ingestion module.

Supports:
  - PDF: direct text extraction per page (pypdf); falls back to rendering
    the page to an image and running Tesseract OCR when a page has little
    or no extractable text (i.e. it's a scanned page).
  - Images (png, jpg, jpeg): OCR via Tesseract directly.
  - Excel (.xlsx): cell text extraction via openpyxl (backend/modules/
    ingestion/excel.py) — no OCR involved.

Fully offline — no network calls. Requires the Tesseract binary to be
installed and on PATH. Requires Poppler (pdftoppm/pdftocairo) to be
installed and on PATH for rendering scanned PDF pages (used by pdf2image).
"""

import logging
import os
import time
from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image
from pdf2image import convert_from_path
from pypdf import PdfReader

from backend.modules.ingestion.excel import extract_excel_text

logger = logging.getLogger(__name__)

# On machines where Tesseract isn't on PATH (e.g. a default Windows install),
# point pytesseract at the known binary location. Guarded by a path check so
# this is a no-op on machines where Tesseract is already discoverable.
_WINDOWS_TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(_WINDOWS_TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = _WINDOWS_TESSERACT_PATH

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg"}
SUPPORTED_PDF_EXTENSIONS = {".pdf"}
SUPPORTED_EXCEL_EXTENSIONS = {".xlsx"}
SUPPORTED_EXTENSIONS = SUPPORTED_IMAGE_EXTENSIONS | SUPPORTED_PDF_EXTENSIONS | SUPPORTED_EXCEL_EXTENSIONS

# Downscale images larger than this (longest side, in px) before OCR so a
# single page/image stays well under the ~5s CPU OCR budget.
MAX_IMAGE_DIMENSION = 2000

# DPI used to rasterize scanned PDF pages. 200 is a good speed/accuracy
# tradeoff for Tesseract on a CPU-only laptop.
PDF_RENDER_DPI = 200

# If a PDF page's directly-extracted text is shorter than this, treat the
# page as scanned/image-only and OCR it instead.
MIN_CHARS_FOR_DIRECT_TEXT = 20


class OCRError(Exception):
    """Raised when a file can't be opened or text can't be extracted from it."""


def _downscale_image_if_needed(image: Image.Image, max_dimension: int = MAX_IMAGE_DIMENSION) -> Image.Image:
    width, height = image.size
    longest_side = max(width, height)
    if longest_side <= max_dimension:
        return image
    scale = max_dimension / longest_side
    new_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    return image.resize(new_size, Image.LANCZOS)


def _ocr_image(image: Image.Image) -> str:
    image = _downscale_image_if_needed(image)
    if image.mode not in ("L", "RGB"):
        image = image.convert("RGB")
    text = pytesseract.image_to_string(image)
    return text.strip()


def extract_text_from_image_file(file_path: str) -> dict:
    """OCR a single image file (png/jpg/jpeg)."""
    try:
        image = Image.open(file_path)
        image.load()
    except Exception as exc:
        raise OCRError(f"Could not open image file: {exc}") from exc

    start = time.monotonic()
    try:
        text = _ocr_image(image)
    except Exception as exc:
        raise OCRError(f"OCR failed on image: {exc}") from exc
    logger.info("OCR on image took %.2fs", time.monotonic() - start)

    pages = [{"page_number": 1, "text": text, "method": "ocr"}]
    return {"full_text": text, "pages": pages}


def _extract_pdf_page_text_direct(reader: PdfReader) -> list:
    page_texts = []
    for page in reader.pages:
        try:
            text = (page.extract_text() or "").strip()
        except Exception:
            text = ""
        page_texts.append(text)
    return page_texts


def extract_text_from_pdf_file(file_path: str) -> dict:
    """
    Extract text from a PDF. Pages with a real text layer are read directly;
    pages that look scanned (little/no extractable text) are rendered to an
    image and OCR'd.
    """
    try:
        reader = PdfReader(file_path)
    except Exception as exc:
        raise OCRError(f"Could not open PDF file: {exc}") from exc

    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except Exception as exc:
            raise OCRError(f"PDF is password-protected and could not be opened: {exc}") from exc

    direct_texts = _extract_pdf_page_text_direct(reader)
    num_pages = len(direct_texts)
    if num_pages == 0:
        raise OCRError("PDF has no pages.")

    pages_needing_ocr = [i for i, t in enumerate(direct_texts) if len(t) < MIN_CHARS_FOR_DIRECT_TEXT]

    rendered_by_index = {}
    if pages_needing_ocr:
        try:
            rendered = convert_from_path(file_path, dpi=PDF_RENDER_DPI)
        except Exception as exc:
            raise OCRError(
                "Failed to render scanned PDF pages for OCR. Make sure Poppler "
                f"is installed and on PATH: {exc}"
            ) from exc
        for idx in pages_needing_ocr:
            if idx < len(rendered):
                rendered_by_index[idx] = rendered[idx]

    pages = []
    for idx in range(num_pages):
        page_number = idx + 1
        if idx in rendered_by_index:
            start = time.monotonic()
            try:
                text = _ocr_image(rendered_by_index[idx])
            except Exception as exc:
                raise OCRError(f"OCR failed on PDF page {page_number}: {exc}") from exc
            logger.info("OCR on PDF page %d took %.2fs", page_number, time.monotonic() - start)
            pages.append({"page_number": page_number, "text": text, "method": "ocr"})
        else:
            pages.append({"page_number": page_number, "text": direct_texts[idx], "method": "direct"})

    full_text = "\n\n".join(p["text"] for p in pages if p["text"])
    return {"full_text": full_text, "pages": pages}


def extract_text_from_excel_file(file_path: str) -> dict:
    """Extract text from an .xlsx workbook via extract_excel_text()."""
    try:
        text = extract_excel_text(file_path)
    except Exception as exc:
        raise OCRError(f"Could not read Excel file: {exc}") from exc

    pages = [{"page_number": 1, "text": text, "method": "excel"}]
    return {"full_text": text, "pages": pages}


def extract_text(file_path: str, original_filename: Optional[str] = None) -> dict:
    """
    Extract text from a PDF, image, or Excel (.xlsx) file.

    Returns:
        {
            "full_text": str,                  # all extracted text, concatenated
            "pages": [                          # per-page (PDF), per-image, or
                                                 # whole-workbook (Excel) breakdown
                {"page_number": int, "text": str, "method": "direct" | "ocr" | "excel"},
                ...
            ],
        }

    Raises:
        OCRError: if the file can't be opened, is an unsupported type, or
            text extraction fails.
    """
    name = original_filename or file_path
    ext = Path(name).suffix.lower()

    if ext in SUPPORTED_EXCEL_EXTENSIONS:
        return extract_text_from_excel_file(file_path)
    if ext in SUPPORTED_PDF_EXTENSIONS:
        return extract_text_from_pdf_file(file_path)
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return extract_text_from_image_file(file_path)
    raise OCRError(
        f"Unsupported file type '{ext}'. Supported types: "
        f"{', '.join(sorted(SUPPORTED_EXTENSIONS))}."
    )
