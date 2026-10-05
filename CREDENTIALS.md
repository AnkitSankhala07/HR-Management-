# 🔐 Dayflow HRMS — Demo Credentials & Access Matrix

All pre-seeded demo accounts in Dayflow HRMS are configured with the shared password below. You can use these accounts to explore the 6-role server-enforced Role-Based Access Control (RBAC) system.

---

## 🔑 Shared Password
```text
Dayflow@2026
```

---

## 👥 Demo Accounts by Role

| Role | Name | Email | Employee ID | Department | Access Level & Permissions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Super Admin** | Sanjay Kapoor | `superadmin@dayflow.dev` | `DF-SA-001` | HR | Full platform configuration, user account management, Django admin panel (`/admin/`), and security audit logs. |
| **HR Admin** | Hetal Shah | `hradmin@dayflow.dev` | `DF-HA-001` | HR | Employee directory management, monthly payroll execution, company attendance, leave approvals, and workforce reports. |
| **HR Manager** | Himani Desai | `hrmanager@dayflow.dev` | `DF-HM-001` | HR | Employee lifecycle records, team attendance monitoring, and leave management. |
| **Manager** | Manav Joshi | `manager@dayflow.dev` | `DF-MG-001` | Engineering | Team oversight, team attendance tracking, employee leave request reviews, goals/OKRs, and interview evaluations. |
| **Recruiter** | Ritika Mehta | `recruiter@dayflow.dev` | `DF-RC-001` | HR | Job openings, recruitment ATS, Kanban pipeline (Applied → Screening → Interview → Offer → Hired), candidates, and offer letter generation. |
| **Employee** | Esha Patel | `employee@dayflow.dev` | `DF-EM-001` | Engineering | Self-service dashboard, daily clock-in/out, leave applications, downloadable PDF salary slips, personal document vault, goals, and skill matrix. |

---

## 🌐 Live Application Links

- **Render Live App**: [https://hr-management-ew2l.onrender.com/](https://hr-management-ew2l.onrender.com/)
- **Vercel Frontend**: [https://hr-management-olive-six.vercel.app/](https://hr-management-olive-six.vercel.app/)
- **Login URL**: [https://hr-management-ew2l.onrender.com/login/](https://hr-management-ew2l.onrender.com/login/)
- **Admin Panel**: [https://hr-management-ew2l.onrender.com/admin/](https://hr-management-ew2l.onrender.com/admin/)
- **Careers Portal**: [https://hr-management-ew2l.onrender.com/careers/](https://hr-management-ew2l.onrender.com/careers/)

---

## 🧪 Quick Test Guide

1. **Test Employee Self-Service**:
   - Log in with `employee@dayflow.dev` / `Dayflow@2026`.
   - Clock in on the attendance widget, apply for a leave request, and view the salary slip.
2. **Test Manager Approval**:
   - Log in with `manager@dayflow.dev` / `Dayflow@2026`.
   - Go to Leave or Attendance to review and approve Esha Patel's request.
3. **Test HR & Payroll**:
   - Log in with `hradmin@dayflow.dev` / `Dayflow@2026`.
   - Run payroll for the month and view analytics.
4. **Test Recruiter Pipeline**:
   - Log in with `recruiter@dayflow.dev` / `Dayflow@2026`.
   - Open ATS Pipeline to drag and drop candidates through hiring stages.
