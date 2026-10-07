import hashlib
import io
import os
from datetime import datetime
from pathlib import Path
from typing import Tuple

import qrcode
from PIL import Image
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

from app.config import settings


class CertificateGenerationException(Exception):
    """Raised when an individual certificate fails to generate."""
    pass


def compute_sha256(file_path: Path) -> str:
    """Compute the SHA-256 hash of a file for integrity and verification."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def generate_qr_code_image(data: str) -> io.BytesIO:
    """Generate a clean QR code PNG in-memory."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=5,
        border=1,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1E293B", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


def draw_certificate_template(
    c: canvas.Canvas,
    width: float,
    height: float,
    recipient_name: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
    certificate_code: str,
    template_title: str = "Certificate of Achievement",
    template_subtitle: str = "is proudly presented to",
) -> None:
    """Draws an elegant, professional certificate on the ReportLab canvas."""

    # 1. Subtle warm background fill
    c.setFillColor(colors.HexColor("#FCFBF7"))
    c.rect(0, 0, width, height, fill=1, stroke=0)

    # 2. Outer decorative Navy border
    navy = colors.HexColor("#0F172A")
    c.setStrokeColor(navy)
    c.setLineWidth(5)
    c.rect(20, 20, width - 40, height - 40)

    # 3. Inner Gold border
    gold = colors.HexColor("#D97706")
    gold_dark = colors.HexColor("#B45309")
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.rect(28, 28, width - 56, height - 56)

    # 4. Corner Ornaments (Geometric Deco Brackets)
    corner_size = 24
    for cx, cy, dx, dy in [
        (28, 28, 1, 1),
        (width - 28, 28, -1, 1),
        (28, height - 28, 1, -1),
        (width - 28, height - 28, -1, -1),
    ]:
        c.setStrokeColor(gold_dark)
        c.setLineWidth(2)
        c.line(cx, cy, cx + (dx * corner_size), cy)
        c.line(cx, cy, cx, cy + (dy * corner_size))

    # 5. Top Ribbon / Emblem Icon
    emblem_y = height - 75
    c.setFillColor(gold)
    c.circle(width / 2, emblem_y, 16, fill=1, stroke=0)
    c.setFillColor(navy)
    c.circle(width / 2, emblem_y, 12, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, emblem_y - 4, "★")

    # 6. Main Certificate Title
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 26)
    c.drawCentredString(width / 2, height - 120, template_title.upper())

    # Decorative separator line under title
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.line((width / 2) - 120, height - 132, (width / 2) + 120, height - 132)

    # 7. Subtitle / Presentation text
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica-Oblique", 13)
    c.drawCentredString(width / 2, height - 160, template_subtitle.upper())

    # 8. Recipient Name (Prominent & Elegant)
    c.setFillColor(colors.HexColor("#0F172A"))
    c.setFont("Helvetica-Bold", 30)
    c.drawCentredString(width / 2, height - 210, recipient_name)

    # Gold Accent underline below name
    c.setStrokeColor(gold)
    c.setLineWidth(2)
    c.line((width / 2) - 180, height - 222, (width / 2) + 180, height - 222)

    # 9. Body description text
    c.setFillColor(colors.HexColor("#334155"))
    c.setFont("Helvetica", 13)
    c.drawCentredString(
        width / 2,
        height - 260,
        "for successfully completing and demonstrating exceptional proficiency in",
    )

    # 10. Event / Course Name
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width / 2, height - 290, event_name)

    # 11. Issuer Acknowledgement
    c.setFillColor(colors.HexColor("#475569"))
    c.setFont("Helvetica", 12)
    c.drawCentredString(width / 2, height - 320, f"conferred by {issuer_name}")

    # 12. Bottom Section: Date, Official Seal, QR Code & Signatures
    bottom_y = 95

    # Left: Issue Date & Line
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1)
    c.line(80, bottom_y + 15, 230, bottom_y + 15)
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(155, bottom_y + 20, issue_date)
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(155, bottom_y + 2, "DATE OF ISSUANCE")

    # Center: Official Seal Badge
    seal_x = width / 2
    seal_y = bottom_y + 20
    c.setStrokeColor(gold)
    c.setLineWidth(1.5)
    c.circle(seal_x, seal_y, 28, fill=0, stroke=1)
    c.setStrokeColor(gold_dark)
    c.circle(seal_x, seal_y, 24, fill=0, stroke=1)
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 7)
    c.drawCentredString(seal_x, seal_y + 8, "OFFICIAL")
    c.drawCentredString(seal_x, seal_y - 2, "VERIFIED")
    c.drawCentredString(seal_x, seal_y - 12, "CREDENTIAL")

    # Right: Signature line & Issuer Signatory
    c.setStrokeColor(colors.HexColor("#94A3B8"))
    c.setLineWidth(1)
    c.line(width - 250, bottom_y + 15, width - 100, bottom_y + 15)
    c.setFillColor(navy)
    c.setFont("Helvetica-Bold", 11)
    c.drawCentredString(width - 175, bottom_y + 20, issuer_name)
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Helvetica", 9)
    c.drawCentredString(width - 175, bottom_y + 2, "AUTHORIZED SIGNATURE")

    # 13. Dynamic QR Code for Instant Mobile Verification
    try:
        verify_url = f"{settings.BASE_URL}/api/v1/certificates/verify/{certificate_code}"
        qr_stream = generate_qr_code_image(verify_url)
        from reportlab.lib.utils import ImageReader
        qr_reader = ImageReader(qr_stream)
        c.drawImage(qr_reader, 45, 38, width=44, height=44, mask="auto")
    except Exception:
        # Graceful degradation if QR rendering fails
        pass

    # 14. Verification ID Footer
    c.setFillColor(colors.HexColor("#64748B"))
    c.setFont("Courier-Bold", 9)
    c.drawString(95, 48, f"VERIFICATION ID: {certificate_code}")
    c.setFont("Helvetica", 8)
    c.drawString(95, 38, "Verify authenticity via scan or portal")


def generate_certificate_pdf(
    recipient_name: str,
    recipient_email: str,
    event_name: str,
    issuer_name: str,
    issue_date: str,
    certificate_code: str,
    output_path: Path,
    template_title: str = "Certificate of Achievement",
    template_subtitle: str = "is proudly presented to",
) -> Tuple[str, int]:
    """
    Renders a certificate to a PDF file at output_path.
    Returns (sha256_checksum, file_size_in_bytes).
    """
    # Trigger simulation failure if requested
    if settings.FAIL_SIMULATION_FLAG in recipient_name or settings.FAIL_SIMULATION_FLAG in recipient_email:
        raise CertificateGenerationException(
            f"Simulated generation failure triggered for recipient: {recipient_name}"
        )

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Setup Landscape A4 Canvas
    page_width, page_height = landscape(A4)
    c = canvas.Canvas(str(output_path), pagesize=(page_width, page_height))
    c.setTitle(f"Certificate - {recipient_name} - {event_name}")
    c.setAuthor(issuer_name)
    c.setSubject(f"{template_title} for {event_name}")

    try:
        draw_certificate_template(
            c=c,
            width=page_width,
            height=page_height,
            recipient_name=recipient_name,
            event_name=event_name,
            issuer_name=issuer_name,
            issue_date=issue_date,
            certificate_code=certificate_code,
            template_title=template_title,
            template_subtitle=template_subtitle,
        )
        c.showPage()
        c.save()
    except Exception as e:
        # Clean up any partial file if generation failed
        if output_path.exists():
            output_path.unlink()
        raise CertificateGenerationException(f"Failed rendering certificate PDF: {str(e)}") from e

    file_size = output_path.stat().st_size
    checksum = compute_sha256(output_path)
    return checksum, file_size
