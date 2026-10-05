"""All analytics are computed from MySQL at request time - nothing is hardcoded or cached in the code."""
from collections import Counter, defaultdict
from datetime import date, timedelta

from sqlalchemy import bindparam, text
from sqlalchemy.engine import Connection

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def _d(v):
    return v if isinstance(v, date) else date.fromisoformat(str(v)[:10])


def last_months(n=6):
    d, out = date.today().replace(day=1), []
    for _ in range(n):
        out.append((d.year, d.month))
        d = (d - timedelta(days=1)).replace(day=1)
    return out[::-1]


def scoped(sql: str, ids, col: str):
    """Append an `AND col IN :ids` clause only when the caller is not allowed to see everyone."""
    if ids is None:
        return text(sql.replace("/*SCOPE*/", "")), None
    if not ids:
        ids = [-1]
    return text(sql.replace("/*SCOPE*/", f" AND {col} IN :ids")).bindparams(bindparam("ids", expanding=True)), ids


def run(conn: Connection, sql: str, ids, col: str, **params):
    stmt, bound = scoped(sql, ids, col)
    return conn.execute(stmt, {**params, **({"ids": bound} if bound is not None else {})}).mappings().all()


def workforce(conn: Connection) -> dict:
    today = date.today()
    q = lambda sql, **p: conn.execute(text(sql), p).scalar() or 0
    total_active = q("SELECT COUNT(*) FROM employees e JOIN users u ON u.id=e.user_id WHERE u.is_active = :t", t=True)
    joins = [(_d(r[0])) for r in conn.execute(text("SELECT e.joining_date FROM employees e JOIN users u ON u.id=e.user_id WHERE u.is_active = :t"), {"t": True})]
    growth = []
    for y, m in last_months():
        end = date(y + (m == 12), (m % 12) + 1, 1)
        growth.append(sum(1 for j in joins if j < end))
    month_start = today.replace(day=1)
    att = conn.execute(text("SELECT status, COUNT(*) c FROM attendance WHERE attendance_date >= :s GROUP BY status"), {"s": today - timedelta(days=30)}).mappings().all()
    tot = sum(r["c"] for r in att)
    present = sum(r["c"] for r in att if r["status"] in ("PRESENT", "WFH", "HALF_DAY"))
    ly, lm = last_months(1)[0]
    tenure = Counter()
    for j in joins:
        yrs = (today - j).days / 365
        tenure["< 1 yr" if yrs < 1 else "1-2 yrs" if yrs < 2 else "2-5 yrs" if yrs < 5 else "5+ yrs"] += 1
    return {
        "cards": {
            "Total Employees": q("SELECT COUNT(*) FROM employees"), "Active Employees": total_active,
            "New Employees": sum(1 for j in joins if j >= month_start),
            "Employees on Leave": q("SELECT COUNT(*) FROM attendance WHERE attendance_date = :d AND status = 'LEAVE'", d=today),
            "Attendance %": round(100 * present / tot, 1) if tot else 0,
            "Pending Leave": q("SELECT COUNT(*) FROM leave_requests WHERE status = 'PENDING'"),
            "Payroll Cost": float(q("SELECT SUM(net_salary) FROM payroll WHERE pay_year=:y AND pay_month=:m", y=ly, m=lm)),
            "Open Jobs": q("SELECT COUNT(*) FROM jobs WHERE status = 'OPEN'"), "Applications": q("SELECT COUNT(*) FROM applications"),
            "Hires": q("SELECT COUNT(*) FROM applications WHERE stage = 'HIRED'"),
        },
        "growth": {"labels": [f"{MONTHS[m - 1]} {str(y)[2:]}" for y, m in last_months()], "data": growth},
        "departments": {r["name"]: r["c"] for r in conn.execute(text("SELECT COALESCE(d.name,'Unassigned') name, COUNT(*) c FROM employees e LEFT JOIN departments d ON d.id=e.department_id GROUP BY d.name")).mappings()},
        "tenure": dict(tenure),
    }


def attendance(conn: Connection, ids) -> dict:
    today = date.today()
    rows = run(conn, "SELECT attendance_date d, status FROM attendance WHERE attendance_date >= :s /*SCOPE*/", ids, "employee_id", s=today - timedelta(days=30))
    by_day, split = defaultdict(lambda: [0, 0]), Counter()
    for r in rows:
        d = _d(r["d"])
        by_day[d][1] += 1
        by_day[d][0] += r["status"] in ("PRESENT", "WFH", "HALF_DAY")
        split[r["status"].replace("_", " ").title()] += 1
    days = sorted(by_day)
    return {"trend": {"labels": [d.strftime("%d %b") for d in days], "data": [round(100 * by_day[d][0] / by_day[d][1], 1) for d in days]}, "split": dict(split)}


def leave(conn: Connection, ids) -> dict:
    rows = run(conn, "SELECT l.start_date, l.total_days, t.name FROM leave_requests l JOIN leave_types t ON t.id=l.leave_type_id WHERE l.status='APPROVED' /*SCOPE*/", ids, "l.employee_id")
    months = last_months()
    trend, types = {m: 0.0 for m in months}, Counter()
    for r in rows:
        d = _d(r["start_date"])
        if (d.year, d.month) in trend:
            trend[(d.year, d.month)] += float(r["total_days"])
        types[r["name"]] += 1
    return {"trend": {"labels": [f"{MONTHS[m - 1]} {str(y)[2:]}" for y, m in months], "data": list(trend.values())}, "types": dict(types)}


def payroll(conn: Connection) -> dict:
    months = last_months()
    trend = []
    for y, m in months:
        trend.append(float(conn.execute(text("SELECT COALESCE(SUM(net_salary),0) FROM payroll WHERE pay_year=:y AND pay_month=:m"), {"y": y, "m": m}).scalar()))
    ly, lm = months[-1]
    by_dep = {r["name"]: float(r["s"]) for r in conn.execute(text(
        "SELECT COALESCE(d.name,'Unassigned') name, SUM(p.net_salary) s FROM payroll p JOIN employees e ON e.id=p.employee_id LEFT JOIN departments d ON d.id=e.department_id "
        "WHERE (p.pay_year*100+p.pay_month) = (SELECT MAX(pay_year*100+pay_month) FROM payroll) GROUP BY d.name")).mappings()}
    buckets = Counter()
    for (v,) in conn.execute(text("SELECT net_salary FROM payroll WHERE (pay_year*100+pay_month) = (SELECT MAX(pay_year*100+pay_month) FROM payroll)")):
        v = float(v)
        buckets["< 30k" if v < 30000 else "30-50k" if v < 50000 else "50-80k" if v < 80000 else "80k+"] += 1
    return {"trend": {"labels": [f"{MONTHS[m - 1]} {str(y)[2:]}" for y, m in months], "data": trend}, "by_department": by_dep, "distribution": dict(buckets)}


def recruitment(conn: Connection) -> dict:
    counts = {r["stage"]: r["c"] for r in conn.execute(text("SELECT stage, COUNT(*) c FROM applications GROUP BY stage")).mappings()}
    order = ["APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "OFFER", "HIRED"]
    return {"funnel": {"labels": [s.title() for s in order], "data": [counts.get(s, 0) for s in order]}, "rejected": counts.get("REJECTED", 0)}


def skills(conn: Connection, ids) -> dict:
    rows = run(conn, "SELECT s.name, COUNT(*) c FROM employee_skills es JOIN skills s ON s.id=es.skill_id WHERE 1=1 /*SCOPE*/ GROUP BY s.name ORDER BY c DESC", ids, "es.employee_id")
    names = [(r["name"], r["c"]) for r in rows]
    return {"top_skills": dict(names[:8]), "gaps": dict(sorted(names, key=lambda x: x[1])[:8])}
