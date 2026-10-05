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

## 🔑 Demo Accounts

All pre-seeded demo accounts use the password: **`Dayflow@2026`**

* **Super Admin**: `superadmin@dayflow.dev`
* **HR Admin**: `hradmin@dayflow.dev`
* **HR Manager**: `hrmanager@dayflow.dev`
* **Manager**: `manager@dayflow.dev`
* **Recruiter**: `recruiter@dayflow.dev`
* **Employee**: `employee@dayflow.dev`

---

## 🌐 URLs & Documentation

* **Web Application**: http://localhost:8000/
* **Public Careers Board**: http://localhost:8000/careers/
* **Django REST API Docs (Swagger)**: http://localhost:8000/api/docs/
* **Django REST API Docs (ReDoc)**: http://localhost:8000/api/redoc/
* **FastAPI Copilot & Analytics Docs**: http://localhost:8001/docs
