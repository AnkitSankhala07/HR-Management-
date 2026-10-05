"""Salary-slip PDF rendering (ReportLab)."""
import calendar
from datetime import date
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN, LIGHT = colors.HexColor("#5A724A"), colors.HexColor("#BCE2A3")


def _money(v) -> str:
    return f"{v:,.2f}"


def salary_slip_pdf(p) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title=f"Salary Slip {p.pay_month}/{p.pay_year}")
    st = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=st["Title"], textColor=GREEN, fontSize=22, alignment=0)
    sub = ParagraphStyle("s", parent=st["Normal"], textColor=colors.HexColor("#818181"))
    e = p.employee
    period = f"{calendar.month_name[p.pay_month]} {p.pay_year}"
    info = Table([
        ["Employee Name", e.full_name, "Employee ID", e.employee_id],
        ["Department", e.department.name if e.department else "-", "Designation", e.designation.title if e.designation else "-"],
        ["Pay Period", period, "Payment Status", p.get_payment_status_display()],
    ], colWidths=[32 * mm, 52 * mm, 32 * mm, 52 * mm])
    info.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                              ("TEXTCOLOR", (2, 0), (2, -1), colors.grey), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    earn = [["Earnings", "Amount (INR)"], ["Basic Salary", _money(p.basic_salary)], ["HRA", _money(p.hra)],
            ["Allowances", _money(p.allowances)], ["Bonus", _money(p.bonus)], ["Gross Salary", _money(p.gross_salary)]]
    ded = [["Deductions", "Amount (INR)"], ["Tax / Other Deductions", _money(p.deductions)], ["Total Deductions", _money(p.deductions)]]

    def styled(data, bold_last=True):
        t = Table(data, colWidths=[110 * mm, 60 * mm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
            ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#EBEBEB")),
            *([("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")] if bold_last else []),
            ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
        return t

    net = Table([["NET SALARY", f"INR {_money(p.net_salary)}"]], colWidths=[110 * mm, 60 * mm])
    net.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), LIGHT), ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                             ("FONTSIZE", (0, 0), (-1, -1), 13), ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                             ("TOPPADDING", (0, 0), (-1, -1), 10), ("BOTTOMPADDING", (0, 0), (-1, -1), 10)]))
    doc.build([Paragraph("DAYFLOW HRMS", h), Paragraph("Every workday, perfectly aligned. &nbsp;|&nbsp; Dayflow Technologies Pvt. Ltd., Ahmedabad, Gujarat, India", sub),
               Spacer(1, 8 * mm), Paragraph(f"<b>Salary Slip - {period}</b>", st["Heading3"]), info, Spacer(1, 6 * mm),
               styled(earn), Spacer(1, 4 * mm), styled(ded), Spacer(1, 4 * mm), net, Spacer(1, 10 * mm),
               Paragraph(f"Generated on {date.today():%d %b %Y}. This is a computer-generated document and needs no signature.", sub)])
    return buf.getvalue()
