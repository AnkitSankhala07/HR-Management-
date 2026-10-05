from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer


def offer_letter_pdf(o) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=22 * mm, rightMargin=22 * mm, topMargin=20 * mm, title="Offer Letter")
    st = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=st["Title"], textColor=colors.HexColor("#5A724A"), alignment=0)
    body = ParagraphStyle("b", parent=st["Normal"], fontSize=11, leading=17)
    c = o.application.candidate
    doc.build([
        Paragraph("DAYFLOW HRMS", h), Paragraph(f"Date: {o.offer_date:%d %B %Y}", body), Spacer(1, 8 * mm),
        Paragraph(f"Dear {c.name},", body), Spacer(1, 4 * mm),
        Paragraph(f"We are delighted to offer you the position of <b>{o.position}</b>"
                  f"{' in the ' + o.department.name + ' department' if o.department else ''} at Dayflow Technologies Pvt. Ltd.", body),
        Spacer(1, 3 * mm),
        Paragraph(f"Your annual compensation will be <b>INR {o.salary:,.2f}</b>. Your proposed date of joining is <b>{o.joining_date:%d %B %Y}</b>.", body),
        Spacer(1, 3 * mm),
        Paragraph(f"This offer is valid until <b>{o.expiry_date:%d %B %Y}</b>. Please accept using the secure link sent to your email.", body),
        Spacer(1, 10 * mm), Paragraph("Warm regards,<br/>Human Resources<br/>Dayflow Technologies Pvt. Ltd.", body)])
    return buf.getvalue()
