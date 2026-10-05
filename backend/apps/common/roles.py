"""Role constants and role groups used by permissions across the project."""
SUPER_ADMIN = "SUPER_ADMIN"
HR_ADMIN = "HR_ADMIN"
HR_MANAGER = "HR_MANAGER"
MANAGER = "MANAGER"
RECRUITER = "RECRUITER"
EMPLOYEE = "EMPLOYEE"

ROLE_CHOICES = [
    (SUPER_ADMIN, "Super Admin"), (HR_ADMIN, "HR Admin"), (HR_MANAGER, "HR Manager"),
    (MANAGER, "Manager"), (RECRUITER, "Recruiter"), (EMPLOYEE, "Employee"),
]
HR_ROLES = (SUPER_ADMIN, HR_ADMIN, HR_MANAGER)        # people operations
PAYROLL_ROLES = (SUPER_ADMIN, HR_ADMIN)               # confidential salary data
ADMIN_ROLES = (SUPER_ADMIN, HR_ADMIN)
RECRUITMENT_ROLES = (SUPER_ADMIN, HR_ADMIN, HR_MANAGER, RECRUITER)
APPROVER_ROLES = HR_ROLES + (MANAGER,)
ALL_ROLES = tuple(r for r, _ in ROLE_CHOICES)
