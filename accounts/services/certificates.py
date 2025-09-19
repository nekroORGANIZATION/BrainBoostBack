# accounts/services/certificates.py
from __future__ import annotations

from io import BytesIO
from datetime import date
from typing import Optional
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.mail import EmailMessage
from django.utils.crypto import get_random_string
from django.utils.text import slugify

from ..models import Certificate

# --- PDF/graphics ---
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader

# --- QR ---
import qrcode


# ---------- fonts ----------
def _register_fonts():
    """Register TrueType fonts and provide names."""
    base = Path(getattr(settings, "BASE_DIR", Path(__file__).resolve().parents[2]))
    fonts_dir = Path(getattr(settings, "CERT_FONTS_DIR", base / "assets" / "fonts"))

    def _safe_register(tt_name: str, filename: str):
        fpath = fonts_dir / filename
        if fpath.exists():
            pdfmetrics.registerFont(TTFont(tt_name, str(fpath)))

    # Primary: Inter; Fallback: DejaVuSans (with Cyrillic)
    _safe_register("Inter", "Inter-Regular.ttf")
    _safe_register("Inter-Bold", "Inter-Bold.ttf")
    _safe_register("DejaVu", "DejaVuSans.ttf")
    _safe_register("DejaVu-Bold", "DejaVuSans-Bold.ttf")

def _font_regular():
    # Prefer Inter, else DejaVu, else Helvetica
    if "Inter" in pdfmetrics.getRegisteredFontNames():
        return "Inter"
    if "DejaVu" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu"
    return "Helvetica"

def _font_bold():
    if "Inter-Bold" in pdfmetrics.getRegisteredFontNames():
        return "Inter-Bold"
    if "DejaVu-Bold" in pdfmetrics.getRegisteredFontNames():
        return "DejaVu-Bold"
    return "Helvetica-Bold"


def _make_qr_png_bytes(text: str, box_size: int = 8, border: int = 2) -> bytes:
    qr = qrcode.QRCode(
        version=None, error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size, border=border
    )
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _draw_centered_text(c: canvas.Canvas, x, y, text, font, size, color):
    c.setFont(font, size)
    c.setFillColor(color)
    c.drawCentredString(x, y, text)


def build_certificate_pdf_en(full_name: str, course_title: str, serial: str, issued: date) -> bytes:
    _register_fonts()
    REG = _font_regular()
    BLD = _font_bold()

    W, H = A4
    M = 18 * mm

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    # palette
    royal = HexColor("#214EEB")
    deep = HexColor("#1F3CF6")
    sky = HexColor("#EFF4FF")
    graph = HexColor("#1E1E1E")
    muted = HexColor("#6B7280")
    gold = HexColor("#C9A227")
    gold_d = HexColor("#A9861D")

    # background
    c.setFillColor(white); c.rect(0, 0, W, H, 0, 1)
    c.setFillColor(sky); c.roundRect(M, M, W-2*M, H-2*M, 14, 0, 1)
    c.setLineWidth(3); c.setStrokeColor(royal)
    c.roundRect(M, M, W-2*M, H-2*M, 14, 1, 0)

    # top badge
    badge_w, badge_h = W - 2*(M + 20*mm), 18*mm
    badge_x, badge_y = (W - badge_w)/2, H - M - badge_h - 8*mm
    c.setFillColor(royal); c.roundRect(badge_x, badge_y, badge_w, badge_h, 9, 0, 1)
    _draw_centered_text(c, W/2, badge_y + badge_h/2 - 5, "CERTIFICATE OF COMPLETION", BLD, 18, white)

    # main text
    y = badge_y - 26*mm
    _draw_centered_text(c, W/2, y + 28, "This certifies that", REG, 12, graph)
    _draw_centered_text(c, W/2, y, full_name, BLD, 30, graph)
    _draw_centered_text(c, W/2, y - 22, "has successfully completed the course", REG, 12, graph)
    _draw_centered_text(c, W/2, y - 44, course_title, BLD, 18, deep)

    # divider
    c.setStrokeColor(HexColor("#D9E2FF")); c.setLineWidth(2)
    c.line(M + 22*mm, y - 58, W - M - 22*mm, y - 58)

    # info row
    info = f"Certificate ID: {serial}   •   Issued on: {issued.isoformat()}   •   Issued by: BrainBoost Academy"
    _draw_centered_text(c, W/2, y - 78, info, REG, 10.5, graph)

    # seal
    seal_r = 20*mm; seal_x = W - M - 30*mm; seal_y = M + 52*mm
    c.setFillColor(gold); c.circle(seal_x, seal_y, seal_r, 0, 1)
    c.setStrokeColor(gold_d); c.setLineWidth(3); c.circle(seal_x, seal_y, seal_r-3, 1, 0)
    _draw_centered_text(c, seal_x, seal_y + 4, "BRAINBOOST", BLD, 10, white)
    _draw_centered_text(c, seal_x, seal_y - 8, "VERIFIED", REG, 8, white)

    # signatures
    base_y = M + 34*mm; left_x = M + 38*mm; right_x = W/2 + 12*mm
    c.setStrokeColor(HexColor("#C8D4FF")); c.setLineWidth(1.2)
    c.line(left_x, base_y, left_x + 62*mm, base_y)
    c.line(right_x, base_y, right_x + 62*mm, base_y)
    _draw_centered_text(c, left_x + 31*mm, base_y + 6, "Signature", BLD, 10, deep)
    _draw_centered_text(c, right_x + 31*mm, base_y + 6, "Signature", BLD, 10, deep)
    _draw_centered_text(c, left_x + 31*mm, base_y - 12, "Academic Director", REG, 9, graph)
    _draw_centered_text(c, right_x + 31*mm, base_y - 12, "Head of Education", REG, 9, graph)

    # QR (verification)
    verify_base = getattr(settings, "CERT_VERIFY_BASE_URL", None)
    if not verify_base:
        # можно прописать в settings, иначе дадим дефолт
        verify_base = getattr(settings, "SITE_URL", "https://example.com") + "/certificates/verify/"
    verify_url = f"{verify_base}{serial}"
    qr_bytes = _make_qr_png_bytes(verify_url, box_size=6, border=1)
    qr_img = ImageReader(BytesIO(qr_bytes))
    qr_size = 28*mm
    qr_x, qr_y = seal_x - qr_size/2, base_y + 22*mm
    c.drawImage(qr_img, qr_x, qr_y, qr_size, qr_size, mask='auto')
    _draw_centered_text(c, seal_x, qr_y - 10, "Scan to verify", REG, 8, muted)

    # footer note
    _draw_centered_text(c, W/2, M + 10*mm, "For verification, contact support@brainboost.com", REG, 8, muted)

    c.showPage()
    c.save()
    pdf = buf.getvalue(); buf.close()
    return pdf


# ---------------- основной сервис (как в прошлый раз, но чуть дополнил) ----------------

def _make_serial() -> str:
    return get_random_string(12).upper()

def _default_from_email() -> str:
    return getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@brainboost.com")

def issue_or_resend_certificate(
    user,
    course,
    *,
    force_regenerate: bool = False,
    email_to: Optional[str] = None,
) -> Certificate:
    cert: Optional[Certificate] = Certificate.objects.filter(user=user, course=course).first()
    need_new_pdf = force_regenerate or cert is None or not getattr(cert, "pdf", None)

    if cert is None:
        cert = Certificate(user=user, course=course)

    if not getattr(cert, "serial", None):
        cert.serial = _make_serial()

    pdf_bytes: Optional[bytes] = None

    if need_new_pdf:
        full_name = getattr(user, "full_name", None) or f"{getattr(user, 'first_name', '')} {getattr(user, 'last_name', '')}".strip() or user.username
        course_title = getattr(course, "title", None) or getattr(course, "name", None) or "Course"
        issued = date.today()

        pdf_bytes = build_certificate_pdf_en(full_name, course_title, cert.serial, issued)

        base = slugify(f"{full_name}-{course_title}") or "certificate"
        filename = f"{base}-{cert.serial}.pdf"
        cert.pdf.save(filename, ContentFile(pdf_bytes), save=False)
        cert.issued_at = issued

    cert.save()

    # email
    recipient = email_to or getattr(user, "email", None)
    if recipient:
        subject = "Your BrainBoost Certificate"
        body = (
            f"Hi {getattr(user, 'first_name', '') or user.username},\n\n"
            f"Congratulations! Your certificate for the course “{getattr(course, 'title', None) or getattr(course, 'name', None) or 'Course'}” is attached.\n"
            f"Certificate ID: {cert.serial}\n"
            f"Issue date: {(cert.issued_at or date.today()):%Y-%m-%d}\n\n"
            "Best regards,\nBrainBoost Academy"
        )
        msg = EmailMessage(subject=subject, body=body, from_email=_default_from_email(), to=[recipient])

        if pdf_bytes is not None:
            msg.attach(getattr(cert.pdf, "name", "certificate.pdf").split("/")[-1], pdf_bytes, "application/pdf")
        elif getattr(cert, "pdf", None):
            try:
                cert.pdf.open("rb")
                msg.attach(cert.pdf.name.split("/")[-1], cert.pdf.read(), "application/pdf")
            finally:
                try:
                    cert.pdf.close()
                except Exception:
                    pass

        msg.send(fail_silently=True)

    return cert


__all__ = ["issue_or_resend_certificate", "build_certificate_pdf_en"]
