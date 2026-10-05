# DAYFLOW HRMS — Every Workday, Perfectly Aligned

A complete, production-ready enterprise Human Resource Management System (HRMS) built with **Django REST Framework** (core HRMS & business logic), **FastAPI** (AI HR Copilot & workforce analytics), and a clean **vanilla JavaScript + CSS** frontend design system.

---

## 🌟 Highlights & Key Features

* **6-Role Server-Enforced RBAC**:
  * **Super Admin**: Full platform configuration, user account management, and security audit logs.
  * **HR Admin**: Employee directory, payroll generation, attendance, leave approval, and workforce reports.
  * **HR Manager**: Employee records, team attendance, and leave management.
  * **Manager**: Team oversight, attendance tracking, leave requests review, goals/OKRs, and interview feedback.
  * **Recruiter**: Job openings, applicant tracking system (ATS), Kanban pipeline, interviews, and offer management.
  * **Employee**: Self-service dashboard, attendance clock-in/out, leave applications, salary slips, document vault, goals, skills, and peer recognition.

* **Core HR Modules**:
  * **Attendance Management**: Daily/weekly/monthly views, clock-in/out, break tracking, and summary statistics.
  * **Leave Management**: Balance tracking (Casual, Sick, Paid), application workflows, manager review & cancellation.
  * **Payroll Engine**: Monthly payslip calculations, salary breakdowns (Basic, HRA, Allowances, Deductions), and PDF slip download.
  * **Document Vault**: Category-based document uploads (Identity, Academic, Employment) with security checks.
  * **Recruitment & ATS**: Public careers portal, job listings, Kanban pipeline (Applied → Screening → Interview → Offer → Hired), and candidate tracking.
  * **Goals & OKRs**: Objective setting, key results, and progress tracking.
  * **Skill Matrix**: Employee skill endorsements and proficiency levels.
  * **Recognition & Social**: Peer kudos and praise wall.
  * **Company Announcements & Notifications**: Real-time updates and notification center.
  * **Security Audit Logs**: Tamper-evident logging of sensitive actions with IP address and user tracking.

* **AI HR Copilot & Analytics**:
  * Natural language querying with server-side RBAC scoping (FastAPI microservice).
  * Workforce analytics, headcount trends, and leave pattern visualisations.

---

## 📂 Project Structure

```
dayflow_hrms/
├── backend/            # Django REST API & server application
│   ├── apps/           # Modular Django apps (accounts, attendance, leave, payroll, etc.)
│   ├── config/         # Django settings (development, production, base) and URLs
│   ├── media/          # Uploaded documents and profile photos
│   └── manage.py       # Django management script
├── fastapi_service/    # FastAPI AI Copilot and Analytics service
│   └── app/            # FastAPI routers, schemas, and AI services
├── frontend/           # Dedicated frontend assets and templates
│   ├── static/         # CSS design system and JavaScript DF client
│   └── templates/      # HTML layouts, dashboards, and pages
├── requirements/       # Python dependencies
│   ├── base.txt
│   ├── dev.txt
│   └── fastapi.txt
├── .env.example        # Environment variable template
└── requirements.txt    # Root requirements
```

---

## 🚀 Getting Started

### 1. Prerequisites
* Python 3.12+
* SQLite (default for standalone local development) or MySQL 8+

### 2. Environment Setup
```bash
# Clone the repository
git clone https://github.com/AnkitSankhala07/HR-Management-.git
cd HR-Management-

# Create and activate virtual environment
python -m venv .venv
# On Windows PowerShell:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements/fastapi.txt

# Set up environment variables
cp .env.example .env
```

### 3. Initialize Database & Seed Demo Data
```bash
python backend/manage.py migrate
python backend/manage.py seed_demo
```

### 4. Run the Services

**Terminal 1 — Django Core (Port 8000):**
```bash
python backend/manage.py runserver 127.0.0.1:8000
```

**Terminal 2 — FastAPI Service (Port 8001):**
```bash
cd fastapi_service
uvicorn app.main:app --port 8001 --reload
```

---

## 🔑 Demo Credentials & Accounts

> 📄 For the complete access permissions matrix and walkthrough, see **[CREDENTIALS.md](CREDENTIALS.md)**.

All pre-seeded demo accounts share the password: **`Dayflow@2026`**

| Role | Name | Email | Password | Primary Permissions |
| :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | Sanjay Kapoor | `superadmin@dayflow.dev` | `Dayflow@2026` | Full platform control, user management, `/admin/`, audit logs |
| **HR Admin** | Hetal Shah | `hradmin@dayflow.dev` | `Dayflow@2026` | Employee records, payroll processing, leave approvals, reports |
| **HR Manager** | Himani Desai | `hrmanager@dayflow.dev` | `Dayflow@2026` | Employee lifecycle, team attendance & leave oversight |
| **Manager** | Manav Joshi | `manager@dayflow.dev` | `Dayflow@2026` | Team oversight, attendance tracking, leave reviews, goals |
| **Recruiter** | Ritika Mehta | `recruiter@dayflow.dev` | `Dayflow@2026` | Jobs, candidate ATS pipeline, interviews, offer letters |
| **Employee** | Esha Patel | `employee@dayflow.dev` | `Dayflow@2026` | Clock-in/out, leave requests, salary slips, goals, skills |

---

## 🌐 Live Deployments & URLs

* **Render Live Application**: [https://hr-management-ew2l.onrender.com/](https://hr-management-ew2l.onrender.com/)
* **Vercel Frontend URL**: [https://hr-management-olive-six.vercel.app/](https://hr-management-olive-six.vercel.app/)
* **Public Careers Board**: [https://hr-management-ew2l.onrender.com/careers/](https://hr-management-ew2l.onrender.com/careers/)
* **Sign In Page**: [https://hr-management-ew2l.onrender.com/login/](https://hr-management-ew2l.onrender.com/login/)
* **Django Admin**: [https://hr-management-ew2l.onrender.com/admin/](https://hr-management-ew2l.onrender.com/admin/)
* **Local Web Application**: http://localhost:8000/
* **Django REST API Docs (Swagger)**: http://localhost:8000/api/docs/
* **FastAPI Copilot & Analytics Docs**: http://localhost:8001/docs

