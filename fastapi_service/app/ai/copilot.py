"""HR Copilot: permission-aware, tool-based question answering.

Design rules (interview talking points):
  1. The model/intent layer NEVER touches the database directly - it can only call the tools below.
  2. Every tool declares the roles allowed to call it and is scoped to what that user may see (self / team / all).
  3. Unauthorised requests raise HTTP 403 - the Copilot cannot be talked into bypassing RBAC.
  4. The Copilot is an assistant: it refuses hiring/firing/promotion/pay/disciplinary decisions outright.
"""
import re
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from ..dependencies import HR, PAYROLL, RECRUITMENT, CurrentUser, visible_employee_ids

IMPERATIVE = re.compile(r"^\W*(please\s+|can you\s+|could you\s+|go ahead and\s+)?(hire|fire|terminate|dismiss|promote|demote|reject|sack|discipline|suspend)\b", re.I)
DECISION = re.compile(r"\b(hire|fire|terminate|dismiss|promote|demote|reject|shortlist|approve|sack|discipline|increase|raise|reduce|cut|decrease)\b.*\b(candidate|applicant|employee|salary|pay|him|her|them|\w+'s)\b", re.I)
OTHERS = re.compile(r"\b(everyone|everybody|all|other|others|someone|somebody|team|department|company|employees|staff|his|her|their|colleague|coworker|manager|boss|supervisor|lead|friend|peer|[a-z]+'s|DF[-\w]*\d|[A-Z]{1,3}-?\d{2,})\b", re.I)
OWN_PAY = re.compile(r"\b(my|mine)\s+(\w+\s+)?(salary|payroll|pay|payslip|pay slip|ctc|compensation|breakdown|earnings|net|gross)\b|\bhow much (do i|am i)\b", re.I)

SUGGESTIONS = {
    "EMPLOYEE": ["Summarize my attendance", "What is my payroll breakdown?", "What is my leave balance?", "What leave policies are available?", "What documents are required for onboarding?"],
    "MANAGER": ["Show me my team's attendance", "How many leave requests are pending?", "Summarize my attendance", "What leave policies are available?"],
    "RECRUITER": ["How many candidates are currently in interview stage?", "Give me a recruitment pipeline summary", "What documents are required for onboarding?"],
    "HR": ["How many employees are on leave today?", "How many employees are absent today?", "How many leave requests are pending?", "Give me the attendance summary for Engineering", "How many employees joined this month?", "Show me department payroll summary"],
}
SUGGESTIONS["HR_MANAGER"] = SUGGESTIONS["HR_ADMIN"] = SUGGESTIONS["SUPER_ADMIN"] = SUGGESTIONS["HR"]


@dataclass
class Answer:
    text: str
    refused: bool = False
    tool: str = ""


def deny(msg="You are not authorised to access that information.") -> HTTPException:
    return HTTPException(403, msg)


def _q(conn, sql, **p):
    return conn.execute(text(sql), p).mappings().all()


def _scalar(conn, sql, **p):
    return conn.execute(text(sql), p).scalar() or 0


def _in_clause(ids):
    return ("", {}) if ids is None else (" AND employee_id IN :ids", {"ids": ids or [-1]})


def _count_attendance(conn, user, status, label):
    if user.role not in HR + ("MANAGER",):
        raise deny("Company/team attendance is only available to HR and managers.")
    ids = visible_employee_ids(conn, user)
    sql = "SELECT COUNT(*) FROM attendance WHERE attendance_date = :d AND status = :s"
    from sqlalchemy import bindparam
    extra, params = _in_clause(ids)
    stmt = text(sql + extra)
    if ids is not None:
        stmt = stmt.bindparams(bindparam("ids", expanding=True))
    n = conn.execute(stmt, {"d": date.today(), "s": status, **params}).scalar() or 0
    scope = "company-wide" if ids is None else "in your team"
    return Answer(f"{n} employee(s) {label} today ({scope}).", tool="attendance_count")


def _attendance_summary(conn, user, ids, title, days=30):
    from sqlalchemy import bindparam
    extra, params = _in_clause(ids)
    stmt = text("SELECT status, COUNT(*) c, COALESCE(SUM(total_hours),0) h FROM attendance WHERE attendance_date >= :s" + extra + " GROUP BY status")
    if ids is not None:
        stmt = stmt.bindparams(bindparam("ids", expanding=True))
    rows = conn.execute(stmt, {"s": date.today() - timedelta(days=days), **params}).mappings().all()
    if not rows:
        return Answer(f"No attendance records found for {title} in the last {days} days.", tool="attendance_summary")
    tot = sum(r["c"] for r in rows)
    parts = ", ".join(f"{r['status'].replace('_', ' ').title()}: {r['c']}" for r in rows)
    present = sum(r["c"] for r in rows if r["status"] in ("PRESENT", "WFH", "HALF_DAY"))
    hours = float(sum(r["h"] for r in rows))
    return Answer(f"Attendance summary for {title} (last {days} days): {parts}. Attendance rate {100 * present / tot:.0f}%, total hours worked {hours:.1f}.", tool="attendance_summary")


def answer(conn: Connection, user: CurrentUser, message: str) -> Answer:
    m = message.strip()
    low = m.lower()
    # 0) autonomous-decision guard
    if IMPERATIVE.search(m) or DECISION.search(m) and not re.search(r"\b(how many|show|list|summar|what|status)\b", low):
        return Answer("I can't make or recommend employment decisions (hiring, rejecting, promoting, firing, or changing pay or discipline). "
                      "I can help you find the information a human decision-maker needs - those decisions must be made by authorised people in Dayflow.", refused=True, tool="refusal")
    mentions_pay = bool(re.search(r"\b(salary|salaries|payroll|pay slip|payslip|ctc|compensation|earn|paid)\b", low))
    # 1) salary / payroll - strictest rules
    if mentions_pay:
        own = bool(OWN_PAY.search(m)) and not re.search(r"\b(everyone|all|team|department|company|others?|manager|boss)\b", low)
        if own or not OTHERS.search(m):
            if not user.emp_id:
                raise deny("No employee profile is linked to your account.")
            r = _q(conn, "SELECT pay_month, pay_year, basic_salary, hra, allowances, bonus, deductions, gross_salary, net_salary, payment_status FROM payroll "
                         "WHERE employee_id = :e ORDER BY pay_year DESC, pay_month DESC LIMIT 1", e=user.emp_id)
            if not r:
                return Answer("There is no payroll published for you yet.", tool="my_payroll")
            p = r[0]
            return Answer(f"Your payroll for {p['pay_month']}/{p['pay_year']} ({p['payment_status'].title()}): basic ₹{float(p['basic_salary']):,.2f}, HRA ₹{float(p['hra']):,.2f}, "
                          f"allowances ₹{float(p['allowances']):,.2f}, bonus ₹{float(p['bonus']):,.2f} → gross ₹{float(p['gross_salary']):,.2f}. "
                          f"Deductions ₹{float(p['deductions']):,.2f}, so net pay is ₹{float(p['net_salary']):,.2f}.", tool="my_payroll")
        if user.role not in PAYROLL:
            raise deny("Salary information for other employees is confidential. You can only ask about your own payroll.")
        rows = _q(conn, "SELECT COALESCE(d.name,'Unassigned') name, COUNT(*) n, SUM(p.net_salary) s FROM payroll p JOIN employees e ON e.id=p.employee_id LEFT JOIN departments d ON d.id=e.department_id "
                        "WHERE (p.pay_year*100+p.pay_month) = (SELECT MAX(pay_year*100+pay_month) FROM payroll) GROUP BY d.name")
        if not rows:
            return Answer("No payroll data is available yet.", tool="department_payroll")
        lines = "; ".join(f"{r['name']}: ₹{float(r['s']):,.0f} net across {r['n']} employees" for r in rows)
        return Answer(f"Department payroll summary (latest period) - {lines}. Total ₹{sum(float(r['s']) for r in rows):,.0f}.", tool="department_payroll")
    # 2) absent / on leave today
    if re.search(r"\b(on leave|away|out of office)\b", low) and re.search(r"\b(today|now|currently)\b", low):
        return _count_attendance(conn, user, "LEAVE", "are on leave")
    if "absent" in low and re.search(r"\b(today|now)\b", low):
        return _count_attendance(conn, user, "ABSENT", "are absent")
    # 3) pending leave
    if re.search(r"pending", low) and "leave" in low:
        ids = visible_employee_ids(conn, user)
        from sqlalchemy import bindparam
        extra, params = _in_clause(ids)
        stmt = text("SELECT COUNT(*) FROM leave_requests WHERE status='PENDING'" + extra)
        if ids is not None:
            stmt = stmt.bindparams(bindparam("ids", expanding=True))
        n = conn.execute(stmt, params).scalar() or 0
        scope = "company-wide" if ids is None else ("in your team" if user.role == "MANAGER" else "of yours")
        return Answer(f"There are {n} pending leave request(s) {scope}.", tool="pending_leave")
    # 4) leave balance / policies
    if "balance" in low and "leave" in low:
        if not user.emp_id:
            raise deny()
        rows = _q(conn, "SELECT t.name, b.allocated, b.used FROM leave_balances b JOIN leave_types t ON t.id=b.leave_type_id WHERE b.employee_id=:e AND b.year=:y AND b.allocated > 0", e=user.emp_id, y=date.today().year)
        return Answer("Your leave balance: " + "; ".join(f"{r['name']} {float(r['allocated']) - float(r['used']):g} left of {float(r['allocated']):g}" for r in rows) + ".", tool="leave_balance") if rows else Answer("No leave balances found for you yet.", tool="leave_balance")
    if re.search(r"leave (polic|types|entitle)|what leave|policies", low):
        rows = _q(conn, "SELECT name, annual_allocation, is_paid FROM leave_types ORDER BY id")
        return Answer("Available leave types: " + "; ".join(f"{r['name']} ({r['annual_allocation']} days/yr, {'paid' if r['is_paid'] else 'unpaid'})" if r["annual_allocation"] else f"{r['name']} ({'paid' if r['is_paid'] else 'unpaid'})" for r in rows)
                      + ". Leave requests need manager/HR approval and cannot overlap existing requests.", tool="leave_policy")
    # 5) attendance summaries
    if "attendance" in low:
        if re.search(r"\b(my|mine)\b|\bfor me\b|\bof me\b", low):
            if not user.emp_id:
                raise deny()
            return _attendance_summary(conn, user, [user.emp_id], "you")
        depts = [r["name"] for r in _q(conn, "SELECT name FROM departments")]
        dept = next((d for d in depts if d.lower() in low), None)
        if user.role in HR:
            if dept:
                ids = [r["id"] for r in _q(conn, "SELECT e.id FROM employees e JOIN departments d ON d.id=e.department_id WHERE d.name=:n", n=dept)]
                return _attendance_summary(conn, user, ids, f"the {dept} department")
            return _attendance_summary(conn, user, None, "the whole company")
        if user.role == "MANAGER":
            ids = visible_employee_ids(conn, user)
            if dept or "team" in low:
                return _attendance_summary(conn, user, ids, "your team")
            return _attendance_summary(conn, user, ids, "your team")
        raise deny("Department and team attendance is only available to HR and managers. Ask about 'my attendance' instead.")
    # 6) joined this month
    if re.search(r"joined|new (hires|employees)|recent hires", low):
        if user.role not in HR:
            raise deny("Hiring statistics are only available to HR.")
        n = _scalar(conn, "SELECT COUNT(*) FROM employees WHERE joining_date >= :s", s=date.today().replace(day=1))
        return Answer(f"{n} employee(s) joined this month.", tool="new_joiners")
    # 7) recruitment
    if re.search(r"candidate|interview|pipeline|recruit|applicant|open jobs|applications", low):
        if user.role not in RECRUITMENT:
            raise deny("Recruitment data is only available to HR and recruiters.")
        rows = _q(conn, "SELECT stage, COUNT(*) c FROM applications GROUP BY stage")
        c = {r["stage"]: r["c"] for r in rows}
        if "interview" in low and "pipeline" not in low:
            return Answer(f"{c.get('INTERVIEW', 0)} candidate(s) are currently in the interview stage.", tool="candidates_in_stage")
        order = ["APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED", "REJECTED"]
        open_jobs = _scalar(conn, "SELECT COUNT(*) FROM jobs WHERE status='OPEN'")
        return Answer(f"Recruitment pipeline: {', '.join(f'{s.title()} {c.get(s, 0)}' for s in order)}. {open_jobs} job(s) are open.", tool="pipeline_summary")
    # 8) onboarding docs
    if "onboarding" in low or "documents" in low and "required" in low:
        return Answer("Documents required for onboarding: government photo ID, signed offer letter, educational certificates, previous experience letters, bank account details, and an emergency contact. "
                      "Upload them in the Document Vault; HR will verify each one.", tool="onboarding_policy")
    return Answer("I can answer questions about your attendance, leave and payroll, team and company attendance (for managers/HR), pending approvals, "
                  "recruitment pipeline (for recruiters/HR) and leave policies. Try one of the suggested questions.", tool="help")
