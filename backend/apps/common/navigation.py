"""Sidebar definition per role (cosmetic only - every URL is also enforced server-side)."""
from . import roles as R

# (label, url, lucide icon, roles allowed)
MENU = [
    ("Dashboard", "/dashboard/", "layout-dashboard", R.ALL_ROLES),
    ("My Profile", "/profile/", "user", R.ALL_ROLES),
    ("My Team", "/team/", "users", (R.MANAGER,)),
    ("Employees", "/employees/", "contact", R.HR_ROLES),
    ("Attendance", "/attendance/", "clock", tuple(r for r in R.ALL_ROLES if r != R.RECRUITER) + (R.RECRUITER,)),
    ("Leave", "/leave/", "calendar-days", R.ALL_ROLES),
    ("Payroll", "/payroll/", "wallet", tuple(r for r in R.ALL_ROLES if r not in (R.RECRUITER, R.MANAGER, R.HR_MANAGER)) + (R.MANAGER, R.HR_MANAGER)),
    ("Documents", "/documents/", "folder-lock", tuple(r for r in R.ALL_ROLES if r != R.RECRUITER)),
    ("Goals", "/goals/", "target", tuple(r for r in R.ALL_ROLES if r != R.RECRUITER)),
    ("Skills", "/skills/", "sparkles", tuple(r for r in R.ALL_ROLES if r != R.RECRUITER)),
    ("Recognition", "/recognition/", "award", R.ALL_ROLES),
    ("Announcements", "/announcements/", "megaphone", R.ALL_ROLES),
    ("Jobs", "/recruitment/jobs/", "briefcase", R.RECRUITMENT_ROLES),
    ("Pipeline", "/recruitment/pipeline/", "kanban", R.RECRUITMENT_ROLES),
    ("Candidates", "/recruitment/candidates/", "user-search", R.RECRUITMENT_ROLES),
    ("Interviews", "/recruitment/interviews/", "message-square", R.RECRUITMENT_ROLES + (R.MANAGER,)),
    ("Offers", "/recruitment/offers/", "file-signature", R.RECRUITMENT_ROLES),
    ("Onboarding", "/onboarding/", "clipboard-check", R.RECRUITMENT_ROLES + (R.EMPLOYEE,)),
    ("Analytics", "/analytics/", "bar-chart-3", R.HR_ROLES + (R.MANAGER, R.RECRUITER)),
    ("Audit Logs", "/audit/", "shield-check", R.ADMIN_ROLES),
    ("HR Copilot", "/copilot/", "bot", R.ALL_ROLES),
]


def menu_for(role: str):
    seen, out = set(), []
    for label, url, icon, roles in MENU:
        if role in roles and url not in seen:
            seen.add(url)
            out.append({"label": label, "url": url, "icon": icon})
    return out
