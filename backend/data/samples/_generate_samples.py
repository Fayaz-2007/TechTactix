"""
One-off script that generates the sample test documents shipped alongside
this project (images + PDFs, one text-layer and one scanned-style). Not
part of the application — safe to delete or re-run any time.
"""

from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

SAMPLES_DIR = Path(__file__).resolve().parent


def _load_font(size):
    for candidate in ("arial.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(candidate, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def make_safety_notice_png():
    img = Image.new("RGB", (1000, 320), "white")
    draw = ImageDraw.Draw(img)
    title_font = _load_font(30)
    body_font = _load_font(22)

    draw.text((30, 20), "SAFETY NOTICE - SECTION 4B", fill="black", font=title_font)
    lines = [
        "All personnel must wear hard hats, safety goggles, and steel-toed",
        "boots before entering the production floor. Hearing protection is",
        "mandatory within 10 meters of any machine exceeding 85 decibels.",
        "Report any damaged PPE to your shift supervisor immediately.",
    ]
    y = 80
    for line in lines:
        draw.text((30, y), line, fill="black", font=body_font)
        y += 40

    path = SAMPLES_DIR / "safety_notice.png"
    img.save(path)
    return path


def make_maintenance_log_jpg():
    img = Image.new("RGB", (1000, 320), "white")
    draw = ImageDraw.Draw(img)
    title_font = _load_font(30)
    body_font = _load_font(22)

    draw.text((30, 20), "MAINTENANCE LOG - PUMP UNIT 7", fill="black", font=title_font)
    lines = [
        "Last inspected: 14 March 2026. Bearing temperature nominal at 42C.",
        "Lubricant level normal. Air filter replaced during this visit.",
        "Next scheduled service: 12 June 2026.",
        "Technician on record: R. Kulkarni.",
    ]
    y = 80
    for line in lines:
        draw.text((30, y), line, fill="black", font=body_font)
        y += 40

    path = SAMPLES_DIR / "maintenance_log.jpg"
    img.convert("RGB").save(path, quality=92)
    return path


def make_inspection_report_pdf():
    """Real text-layer PDF (exercises direct pypdf extraction, no OCR)."""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "Pressure Vessel Inspection Report", ln=True)
    pdf.set_font("Helvetica", "", 12)
    pdf.ln(4)

    paragraphs = [
        "Facility: Sector 7 Chemical Processing Unit. Inspection date: 03 "
        "February 2026. Inspector: A. Fernandes, certified pressure "
        "equipment engineer, license PE-44210.",
        "Vessel V-12 was inspected for structural integrity, wall "
        "thickness, and signs of corrosion. Ultrasonic thickness testing "
        "was performed at twelve points around the shell. All readings "
        "were within acceptable tolerance, with the thinnest measurement "
        "at 94% of nominal wall thickness.",
        "No active corrosion, pitting, or weld defects were observed. The "
        "relief valve was tested and released at the rated set pressure of "
        "150 psi. The vessel is approved for continued service.",
        "Recommendation: Vessel V-12 must be re-inspected no later than 03 "
        "February 2027, in accordance with the annual pressure vessel "
        "inspection schedule. Any deviation from this schedule requires "
        "written approval from the plant safety officer.",
    ]
    for paragraph in paragraphs:
        pdf.multi_cell(0, 7, paragraph)
        pdf.ln(3)

    path = SAMPLES_DIR / "inspection_report.pdf"
    pdf.output(str(path))
    return path


def make_incident_report_scanned_pdf():
    """Image-only PDF (no text layer) — exercises the OCR-fallback path."""
    img = Image.new("RGB", (1000, 420), "white")
    draw = ImageDraw.Draw(img)
    title_font = _load_font(28)
    body_font = _load_font(20)

    draw.text((30, 20), "INCIDENT REPORT - WORKSHOP FLOOR", fill="black", font=title_font)
    lines = [
        "Date: 02 August 2026, 14:20 hrs.",
        "A minor chemical spill occurred near Tank 3 during a scheduled",
        "transfer operation. Approximately 2 liters of solvent leaked from",
        "a loose coupling. The area was cordoned off within 5 minutes and",
        "no injuries were reported.",
        "The spill kit was deployed per protocol SOP-118 and the area was",
        "cleared for re-entry after ventilation checks passed.",
        "Investigation has been assigned to the EHS team, with a full",
        "report due within 5 working days.",
    ]
    y = 80
    for line in lines:
        draw.text((30, y), line, fill="black", font=body_font)
        y += 36

    path = SAMPLES_DIR / "incident_report_scanned.pdf"
    img.save(path)
    return path


def main():
    created = [
        make_safety_notice_png(),
        make_maintenance_log_jpg(),
        make_inspection_report_pdf(),
        make_incident_report_scanned_pdf(),
    ]
    for path in created:
        print(f"created {path} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
