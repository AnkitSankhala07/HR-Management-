# Frontend — Dayflow HRMS

This directory contains the entire frontend layer of Dayflow HRMS:

```
frontend/
├── static/
│   ├── css/
│   │   └── app.css       # Complete CSS design system, themes, and utility classes
│   └── js/
│       └── app.js        # Core frontend logic: DF client (API, tables, modals, toasts)
└── templates/
    ├── base.html         # Root HTML wrapper (meta, fonts, libraries)
    ├── app_base.html     # Authenticated shell (sidebar, navigation, top bar, search)
    ├── landing.html      # Public landing page
    ├── auth/             # Sign in, Sign up, Forgot/Reset password, Verify email
    ├── dashboards/       # Role-specific dashboards (Employee, Manager, HR Admin, Recruiter)
    ├── pages/            # Modules (Attendance, Leave, Payroll, Documents, Goals, Skills, etc.)
    ├── public/           # Public careers portal & offer accept page
    └── errors/           # 403, 404, 500 error templates
```

### Configuration
Django is configured in `backend/config/settings/base.py` to serve templates and static assets directly from this directory:
- `TEMPLATES[0]["DIRS"] = [FRONTEND_DIR / "templates"]`
- `STATICFILES_DIRS = [FRONTEND_DIR / "static"]`
