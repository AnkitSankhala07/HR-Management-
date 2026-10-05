"""Seed realistic fictional demo data. DEVELOPMENT ONLY - credentials are documented in the README."""
import random
from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.announcements.models import Announcement
from apps.attendance.models import Attendance
from apps.common import roles as R
from apps.employees.models import Department, Designation, Employee
from apps.employees.services import create_employee
from apps.goals.models import Goal
from apps.leave.models import LeaveBalance, LeaveRequest, LeaveType
from apps.leave.services import ensure_balances, ensure_leave_types, working_days
from apps.payroll.models import Payroll
from apps.recognition.models import Recognition
from apps.recruitment.models import Application, Candidate, Interview, Job
from apps.skills.models import EmployeeSkill, Skill

User = get_user_model()
DEMO_PASSWORD = "Dayflow@2026"
FIRST = "Aarav Vivaan Aditya Ishaan Kabir Rohan Arjun Neel Dev Yash Meera Anaya Diya Isha Kavya Riya Saanvi Tara Nisha Pooja Rahul Karan Mehul Hardik Jainam Priya Sneha Urvi Zeel Krish Parth Dhruv Harsh Om Smit Bhavya Esha Jiya Khushi Mansi Naina Palak Ria Sia Tanvi Vani Yuvraj Chirag Darshan Falguni".split()
LAST = "Patel Shah Mehta Desai Joshi Trivedi Parmar Sharma Gupta Nair Iyer Reddy Kapoor Bhatt Chauhan Solanki Thakkar Vyas Pandya Modi".split()
DEPTS = {"Engineering": ["Software Engineer", "Senior Software Engineer", "QA Engineer", "Engineering Manager"],
         "HR": ["HR Executive", "HR Manager", "Recruiter"], "Finance": ["Accountant"], "Sales": ["Sales Executive"], "Marketing": ["Marketing Executive"]}
SKILLS = ["Python", "Django", "SQL", "Docker", "FastAPI", "JavaScript", "Communication", "Leadership", "Excel", "Recruiting", "Figma", "Testing"]


class Command(BaseCommand):
    help = "Seed demo data (50 employees, attendance, leave, payroll, goals, skills, recruitment...)"

    def add_arguments(self, p):
        p.add_argument("--reset", action="store_true", help="Delete existing demo data first")

    @transaction.atomic
    def handle(self, *a, **o):
        random.seed(42)
        if User.objects.filter(email="employee@dayflow.dev").exists() and not o["reset"]:
            self.stdout.write("Demo data already present (use --reset to rebuild).")
            return
        if o["reset"]:
            User.objects.all().delete(); Department.objects.all().delete(); Job.objects.all().delete(); Candidate.objects.all().delete(); Announcement.objects.all().delete(); Skill.objects.all().delete()
        ensure_leave_types()
        depts, desigs = {}, {}
        for d, titles in DEPTS.items():
            depts[d] = Department.objects.get_or_create(name=d, defaults={"description": f"{d} department"})[0]
            for t in titles:
                desigs[t] = Designation.objects.get_or_create(title=t, department=depts[d])[0]
        today = date.today()
        mk = lambda eid, email, first, last, role, dept, desig, mgr=None, years=2: create_employee(
            employee_id=eid, email=email, first_name=first, last_name=last, password=DEMO_PASSWORD, role=role,
            department=depts[dept], designation=desigs[desig], manager=mgr, phone=f"+9198{random.randint(10000000, 99999999)}",
            joining_date=today - timedelta(days=int(365 * years) + random.randint(0, 200)), date_of_birth=date(1990 + random.randint(0, 10), random.randint(1, 12), random.randint(1, 28)),
            city="Ahmedabad", state="Gujarat", address=f"{random.randint(1, 99)} SG Highway")
        # ---- named demo accounts
        mk("DF-SA-001", "superadmin@dayflow.dev", "Sanjay", "Kapoor", R.SUPER_ADMIN, "HR", "HR Manager", years=5)
        hra = mk("DF-HA-001", "hradmin@dayflow.dev", "Hetal", "Shah", R.HR_ADMIN, "HR", "HR Manager", years=4)
        mk("DF-HM-001", "hrmanager@dayflow.dev", "Himani", "Desai", R.HR_MANAGER, "HR", "HR Executive", years=3)
        mgr = mk("DF-MG-001", "manager@dayflow.dev", "Manav", "Joshi", R.MANAGER, "Engineering", "Engineering Manager", years=4)
        mk("DF-RC-001", "recruiter@dayflow.dev", "Ritika", "Mehta", R.RECRUITER, "HR", "Recruiter", years=2)
        mk("DF-EM-001", "employee@dayflow.dev", "Esha", "Patel", R.EMPLOYEE, "Engineering", "Software Engineer", mgr, years=1)
        # ---- bulk employees to reach 50
        roster = [e for e in Employee.objects.all()]
        names = [(f, l) for f in FIRST for l in LAST]
        random.shuffle(names)
        plan = [("Engineering", ["Software Engineer"] * 14 + ["Senior Software Engineer"] * 6 + ["QA Engineer"] * 5), ("HR", ["HR Executive"] * 3), ("Finance", ["Accountant"] * 5),
                ("Sales", ["Sales Executive"] * 6), ("Marketing", ["Marketing Executive"] * 5)]
        n = 2
        for dept, ds in plan:
            for ds_ in ds:
                if Employee.objects.count() >= 50:
                    break
                f, l = names.pop()
                mk(f"DF-{n:03d}", f"{f.lower()}.{l.lower()}{n}@dayflow.dev", f, l, R.EMPLOYEE, dept, ds_, mgr if dept == "Engineering" else None, years=random.uniform(0.2, 5))
                n += 1
        emps = list(Employee.objects.select_related("user", "department"))
        self.stdout.write(f"Employees: {len(emps)}")
        # ---- attendance (last 30 working days)
        now = timezone.now()
        for e in emps:
            for i in range(1, 31):
                d = today - timedelta(days=i)
                if d.weekday() >= 5 or d < e.joining_date:
                    continue
                r = random.random()
                if r < 0.04:
                    Attendance.objects.create(employee=e, attendance_date=d, status="ABSENT"); continue
                hrs = Decimal(str(round(random.uniform(7.2, 9.6), 2)))
                ci = timezone.make_aware(timezone.datetime.combine(d, timezone.datetime.min.time())) + timedelta(hours=9, minutes=random.randint(0, 40))
                Attendance.objects.create(employee=e, attendance_date=d, check_in=ci, check_out=ci + timedelta(hours=float(hrs)), total_hours=hrs,
                                          overtime_hours=max(hrs - 8, Decimal("0")), status="WFH" if r > 0.92 else "PRESENT")
        # ---- leave
        lts = {t.code: t for t in LeaveType.objects.all()}
        for e in random.sample(emps, 18):
            code = random.choice(["PAID", "SICK", "CASUAL"])
            start = today + timedelta(days=random.randint(-12, 20))
            while start.weekday() >= 5:
                start += timedelta(days=1)
            end = start + timedelta(days=random.randint(0, 2))
            days = len(working_days(start, end))
            st = random.choice(["PENDING", "PENDING", "APPROVED", "APPROVED", "REJECTED"])
            lr = LeaveRequest.objects.create(employee=e, leave_type=lts[code], start_date=start, end_date=end, total_days=days, reason="Personal work", status=st,
                                             reviewed_by=hra.user if st != "PENDING" else None, reviewed_at=now if st != "PENDING" else None, admin_comment="Approved" if st == "APPROVED" else ("Please reschedule" if st == "REJECTED" else ""))
            if st == "APPROVED":
                b = LeaveBalance.objects.get(employee=e, leave_type=lts[code], year=start.year); b.used += days; b.save()
                for d in working_days(start, end):
                    Attendance.objects.update_or_create(employee=e, attendance_date=d, defaults={"status": "LEAVE", "check_in": None, "check_out": None, "total_hours": 0, "overtime_hours": 0})
        # ---- payroll (last 3 months)
        for e in emps:
            basic = Decimal(random.choice([30000, 38000, 45000, 55000, 70000, 90000]))
            for k in range(1, 4):
                m = today.month - k
                y = today.year + (m - 1) // 12 if m < 1 else today.year
                m = (m - 1) % 12 + 1
                p = Payroll(employee=e, pay_month=m, pay_year=y, basic_salary=basic, hra=basic * Decimal("0.4"), allowances=Decimal(random.choice([2000, 3500, 5000])),
                            bonus=Decimal(random.choice([0, 0, 2000, 5000])), deductions=basic * Decimal("0.12"), payment_status="PAID", updated_by=hra.user)
                p.recalculate(); p.save()
        # ---- skills, goals, recognition
        skills = {s: Skill.objects.get_or_create(name=s)[0] for s in SKILLS}
        for e in emps:
            for s in random.sample(SKILLS, 3):
                EmployeeSkill.objects.create(employee=e, skill=skills[s], level=random.randint(1, 4), years_experience=random.randint(0, 6))
            for t in random.sample(["Ship Q4 feature", "Complete certification", "Improve test coverage", "Mentor a junior", "Reduce ticket backlog"], 2):
                g = Goal(owner=e, manager=e.manager, title=t, due_date=today + timedelta(days=random.randint(-10, 60)), progress=random.choice([0, 20, 40, 60, 80, 100]), priority=random.choice(["LOW", "MEDIUM", "HIGH"])); g.save()
        cats, badges = [c for c, _ in Recognition.CATEGORIES], [b for b, _ in Recognition.BADGES]
        for _ in range(15):
            a, b = random.sample(emps, 2)
            Recognition.objects.create(giver=a, receiver=b, category=random.choice(cats), badge=random.choice(badges), message=random.choice(["Excellent contribution to the project.", "Great teamwork this sprint!", "Fantastic problem solving under pressure."]))
        for t, pr in [("Welcome to Dayflow HRMS", "NORMAL"), ("Quarterly town hall this Friday", "IMPORTANT"), ("Office closed for Diwali", "URGENT")]:
            Announcement.objects.create(title=t, description=f"{t}. Please check the calendar for details.", priority=pr, created_by=hra.user)
        # ---- recruitment
        rec = User.objects.get(email="recruiter@dayflow.dev")
        jobs = [Job.objects.create(title=t, department=depts["Engineering"], designation=desigs["Software Engineer"], hiring_manager=mgr, description=f"We are hiring a {t}. Build APIs and services with a great team.",
                                   skills_required="Python, Django, SQL", experience_min=1, status="OPEN", published_at=now, created_by=rec) for t in ("Python Backend Developer", "Full-Stack Developer")]
        stages = ["APPLIED", "APPLIED", "SCREENING", "SHORTLISTED", "INTERVIEW", "INTERVIEW", "REJECTED"]
        for i in range(12):
            c = Candidate.objects.create(name=f"{random.choice(FIRST)} {random.choice(LAST)}", email=f"candidate{i}@example.com", phone="+919800000000", skills="Python, SQL", experience_years=random.randint(0, 6),
                                         education="B.Tech CSE", current_company=random.choice(["Infosys", "TCS", "Startup X", ""]), expected_salary=random.choice([600000, 900000, 1200000]), source=random.choice(["Careers Page", "LinkedIn", "Referral"]))
            app = Application.objects.create(candidate=c, job=random.choice(jobs), stage=random.choice(stages))
            if app.stage == "INTERVIEW":
                iv = Interview.objects.create(application=app, interview_type="TECHNICAL", scheduled_at=now + timedelta(days=random.randint(1, 7)), meeting_link="https://meet.example.com/dayflow")
                iv.interviewers.set([mgr])
        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write(f"Demo logins (password: {DEMO_PASSWORD}): superadmin@ hradmin@ hrmanager@ manager@ recruiter@ employee@ dayflow.dev")
