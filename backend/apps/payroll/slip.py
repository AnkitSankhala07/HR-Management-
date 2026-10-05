"""Professional PDF salary slip (ReportLab)."""
import calendar
import io
from datetime import date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

GREEN, LIGHT = colors.HexColor("#5A724A"), colors.HexColor("#BCE2A3")


def build_salary_slip(p) -> bytes:
    e = p.employee
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm)
    ss = getSampleStyleSheet()
    h = ParagraphStyle("h", parent=ss["Title"], textColor=GREEN, fontSize=22, alignment=0)
    sub = ParagraphStyle("s", parent=ss["Normal"], textColor=colors.HexColor("#818181"))
    money = lambda v: f"{v:,.2f}"
    period = f"{calendar.month_name[p.pay_month]} {p.pay_year}"
    els = [Paragraph("DAYFLOW HRMS", h), Paragraph("Every workday, perfectly aligned. &nbsp;|&nbsp; Dayflow Technologies Pvt. Ltd., Ahmedabad, Gujarat, India", sub),
           Spacer(1, 8), Paragraph(f"<b>Salary Slip - {period}</b>", ss["Heading2"])]
    info = Table([
        ["Employee Name", e.full_name, "Employee ID", e.employee_id],
        ["Department", e.department.name if e.department else "-", "Designation", e.designation.title if e.designation else "-"],
        ["Pay Period", period, "Payment Status", p.get_payment_status_display()],
    ], colWidths=[34 * mm, 52 * mm, 34 * mm, 52 * mm])
    info.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#F8F8F8")),
                              ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#EBEBEB")),
                              ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"), ("FONTNAME", (2, 0), (2, -1), "Helvetica-Bold")]))
    rows = [["Earnings", "Amount (INR)", "Deductions", "Amount (INR)"],
            ["Basic Salary", money(p.basic_salary), "Tax / Other Deductions", money(p.deductions)],
            ["HRA", money(p.hra), "", ""], ["Allowances", money(p.allowances), "", ""], ["Bonus", money(p.bonus), "", ""],
            ["Gross Salary", money(p.gross_salary), "Total Deductions", money(p.deductions)]]
    t = Table(rows, colWidths=[46 * mm, 40 * mm, 46 * mm, 40 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), GREEN), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                           ("BACKGROUND", (0, -1), (-1, -1), LIGHT), ("ALIGN", (1, 0), (1, -1), "RIGHT"), ("ALIGN", (3, 0), (3, -1), "RIGHT"),
                           ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#EBEBEB")), ("FONTSIZE", (0, 0), (-1, -1), 9),
                           ("TOPPADDING", (0, 0), (-1, -1), 6), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    net = Table([["NET SALARY", f"INR {money(p.net_salary)}"]], colWidths=[86 * mm, 86 * mm])
    net.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), GREEN), ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
                             ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"), ("FONTSIZE", (0, 0), (-1, -1), 12),
                             ("ALIGN", (1, 0), (1, 0), "RIGHT"), ("TOPPADDING", (0, 0), (-1, -1), 8), ("BOTTOMPADDING", (0, 0), (-1, -1), 8)]))
    els += [info, Spacer(1, 10), t, Spacer(1, 10), net, Spacer(1, 14),
            Paragraph(f"Generated on {date.today():%d %b %Y}. This is a system-generated document and does not require a signature.", sub)]
    doc.build(els)
    return buf.getvalue()
