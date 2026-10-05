"""Management command to add rich sample data: documents, today's attendance, careers jobs, candidates, announcements, recognitions."""
from datetime import date, timedelta
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.employees.models import Employee, Department, Designation
from apps.documents.models import Document
from apps.attendance.models import Attendance
from apps.recruitment.models import Job, Candidate, Application, Interview
from apps.announcements.models import Announcement
from apps.recognition.models import Recognition


class Command(BaseCommand):
    help = "Add rich sample data (documents, jobs, candidates, announcements, attendance, recognition)"

    def handle(self, *args, **options):
        today = date.today()
        now = timezone.now()

        # 1. Fetch key demo users
        emp = Employee.objects.filter(user__email="employee@dayflow.dev").first()
        mgr = Employee.objects.filter(user__email="manager@dayflow.dev").first()
        hra = Employee.objects.filter(user__email="hradmin@dayflow.dev").first()
        rec = Employee.objects.filter(user__email="recruiter@dayflow.dev").first()
        super_admin = Employee.objects.filter(user__email="superadmin@dayflow.dev").first()

        sample_pdf = (
            b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n"
            b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n"
            b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>\nendobj\n"
            b"xref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000060 00000 n\n0000000117 00000 n\n"
            b"trailer\n<< /Size 4 /Root 1 0 R >>\nstartxref\n190\n%%EOF\n"
        )

        # 2. Add sample documents if not already present
        if emp and Document.objects.filter(employee=emp).count() == 0:
            docs_to_add = [
                ("Offer Letter - Software Engineer", Document.Category.OFFER, Document.Status.VERIFIED, "offer_letter.pdf", hra.user),
                ("Degree Certificate - Computer Science", Document.Category.CERT, Document.Status.VERIFIED, "degree_certificate.pdf", hra.user),
                ("National Identity Card (Aadhaar/Passport)", Document.Category.IDENTITY, Document.Status.VERIFIED, "identity_proof.pdf", hra.user),
                ("Relieving & Experience Letter", Document.Category.EXPERIENCE, Document.Status.PENDING, "experience_letter.pdf", None),
            ]
            for title, cat, status, fname, verifier in docs_to_add:
                doc = Document(
                    employee=emp,
                    category=cat,
                    title=title,
                    original_name=fname,
                    mime_type="application/pdf",
                    size=len(sample_pdf),
                    status=status,
                    uploaded_by=emp.user,
                    verified_by=verifier,
                )
                doc.file.save(f"{emp.employee_id}_{fname}", ContentFile(sample_pdf), save=True)
            self.stdout.write(self.style.SUCCESS("Added sample documents for Employee Esha Patel."))

        # 3. Add today's live attendance for demo employees
        for person, hours in [
            (emp, 3.5),
            (mgr, 4.0),
            (hra, 3.8),
            (rec, 3.0),
        ]:
            if person:
                att, created = Attendance.objects.get_or_create(
                    employee=person,
                    attendance_date=today,
                    defaults={
                        "check_in": now - timedelta(hours=hours),
                        "status": Attendance.Status.PRESENT,
                        "total_hours": hours,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f"Recorded today's attendance for {person.full_name}."))

        # 4. Add rich Careers Jobs
        eng_dept = Department.objects.filter(name="Engineering").first()
        hr_dept = Department.objects.filter(name="HR").first()

        new_jobs = [
            {
                "title": "Senior Frontend Engineer (React/TypeScript)",
                "dept": eng_dept,
                "location": "Ahmedabad / Remote",
                "description": "We are seeking a seasoned Frontend Engineer with deep experience in React, TypeScript, and modern design systems to elevate Dayflow's frontend user experience.",
                "skills_required": "React, TypeScript, CSS3, REST APIs, Design Systems",
                "experience_min": 4,
                "status": Job.Status.OPEN,
            },
            {
                "title": "Product UI/UX Designer",
                "dept": eng_dept,
                "location": "Ahmedabad, India",
                "description": "Join our product design team to craft delightful enterprise HR experiences. You will design web workflows, wireframes, and high-fidelity Figma prototypes.",
                "skills_required": "Figma, User Research, Wireframing, Prototyping",
                "experience_min": 3,
                "status": Job.Status.OPEN,
            },
            {
                "title": "HR Operations & People Partner",
                "dept": hr_dept,
                "location": "Ahmedabad, India",
                "description": "Lead day-to-day employee lifecycle operations, onboarding programs, policy administration, and culture initiatives.",
                "skills_required": "HR Generalist, Employee Relations, Onboarding, Compliance",
                "experience_min": 3,
                "status": Job.Status.OPEN,
            }
        ]

        for jd in new_jobs:
            if jd["dept"] and not Job.objects.filter(title=jd["title"]).exists():
                job = Job.objects.create(
                    title=jd["title"],
                    department=jd["dept"],
                    location=jd["location"],
                    description=jd["description"],
                    skills_required=jd["skills_required"],
                    experience_min=jd["experience_min"],
                    status=jd["status"],
                    created_by=rec.user if rec else None,
                    published_at=now - timedelta(days=2),
                )
                self.stdout.write(self.style.SUCCESS(f"Created open job: {job.title}"))

                # Add sample candidates and applications for this job
                candidates_data = [
                    ("Aakash Varma", f"aakash.{job.pk}@example.com", "+919876543210", 4, Application.Stage.SHORTLISTED),
                    ("Sneha Kulkarni", f"sneha.{job.pk}@example.com", "+919876543211", 5, Application.Stage.INTERVIEW),
                    ("Rohan Mathur", f"rohan.{job.pk}@example.com", "+919876543212", 3, Application.Stage.SCREENING),
                ]
                for name, email, phone, exp, stage in candidates_data:
                    cand, _ = Candidate.objects.get_or_create(
                        email=email,
                        defaults={"name": name, "phone": phone, "experience_years": exp, "skills": "React, TypeScript, UI/UX"}
                    )
                    app, app_created = Application.objects.get_or_create(
                        candidate=cand,
                        job=job,
                        defaults={"stage": stage, "notes": f"Passionate about joining Dayflow as {job.title}."}
                    )
                    if stage == Application.Stage.INTERVIEW and mgr:
                        Interview.objects.get_or_create(
                            application=app,
                            interview_type="TECHNICAL",
                            defaults={
                                "scheduled_at": now + timedelta(days=1),
                                "status": "SCHEDULED",
                            }
                        )

        # 5. Add announcements
        announcements_data = [
            ("Annual Company Retreat & Tech Hackathon 2026", "We are excited to announce Dayflow's annual 3-day retreat and hackathon in Goa from Nov 15-18! More details and team registrations opening next week.", Announcement.Priority.IMPORTANT),
            ("New Health & Wellness Benefits Launched", "Comprehensive medical insurance coverage has been updated to include mental wellness counseling and subsidized annual gym memberships.", Announcement.Priority.NORMAL),
            ("Quarterly Town Hall & Product Roadmap Q4", "Join our CEO and executive team this Friday at 4:00 PM IST for our Quarterly Town Hall reviewing our growth and product milestones.", Announcement.Priority.URGENT),
        ]

        for title, desc, prio in announcements_data:
            if not Announcement.objects.filter(title=title).exists():
                Announcement.objects.create(
                    title=title,
                    description=desc,
                    priority=prio,
                    created_by=hra.user if hra else None,
                )
                self.stdout.write(self.style.SUCCESS(f"Published announcement: {title}"))

        # 6. Add Recognition Kudos
        if emp and mgr:
            recs = [
                (mgr, emp, "PROBLEM_SOLVER", "INNOVATION", "Delivered the backend authentication security hardening ahead of schedule with 100% test coverage!"),
                (hra, mgr, "LEADER", "LEADERSHIP", "Exemplary leadership mentoring the engineering squad and fostering exceptional team collaboration this sprint."),
                (rec, emp, "TEAM_PLAYER", "TEAMWORK", "Appreciate your thorough technical feedback during the senior developer hiring loops!"),
            ]
            for giver, receiver, badge, cat, msg in recs:
                if not Recognition.objects.filter(giver=giver, receiver=receiver, badge=badge).exists():
                    Recognition.objects.create(
                        giver=giver,
                        receiver=receiver,
                        badge=badge,
                        category=cat,
                        message=msg,
                    )
                    self.stdout.write(self.style.SUCCESS(f"Added recognition from {giver.full_name} to {receiver.full_name}."))

        self.stdout.write(self.style.SUCCESS("Sample data enrichment complete!"))
