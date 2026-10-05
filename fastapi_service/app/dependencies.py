"""Auth for the FastAPI service.

The browser obtains a short-lived JWT from Django (/api/auth/service-token/). The token only proves *who*;
role, active flag and team membership are ALWAYS re-read from MySQL so a demoted/deactivated user loses access at once.
"""
from dataclasses import dataclass

import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.engine import Connection

from .config import settings
from .db import engine

HR = ("SUPER_ADMIN", "HR_ADMIN", "HR_MANAGER")
PAYROLL = ("SUPER_ADMIN", "HR_ADMIN")
RECRUITMENT = HR + ("RECRUITER",)


@dataclass
class CurrentUser:
    id: int
    role: str
    emp_id: int | None
    name: str


def get_conn():
    with engine.connect() as conn:
        yield conn


def current_user(authorization: str | None = Header(default=None), conn: Connection = Depends(get_conn)) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "Missing bearer token")
    try:
        claims = jwt.decode(authorization.split(" ", 1)[1], settings.jwt_secret, algorithms=["HS256"], issuer="dayflow-django")
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid token")
    row = conn.execute(text("SELECT u.id, u.role, u.is_active, e.id AS emp_id, e.first_name, e.last_name FROM users u "
                            "LEFT JOIN employees e ON e.user_id = u.id WHERE u.id = :i"), {"i": int(claims["sub"])}).mappings().first()
    if not row or not row["is_active"]:
        raise HTTPException(401, "Account inactive")
    return CurrentUser(row["id"], row["role"], row["emp_id"], f"{row['first_name'] or ''} {row['last_name'] or ''}".strip())


def require(*roles: str):
    def dep(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(403, "You do not have permission to access this resource.")
        return user
    return dep


def visible_employee_ids(conn: Connection, user: CurrentUser) -> list[int] | None:
    """None = everyone (HR). Managers = self + direct reports. Everyone else = self only."""
    if user.role in HR:
        return None
    if user.emp_id is None:
        return []
    if user.role == "MANAGER":
        ids = [r[0] for r in conn.execute(text("SELECT id FROM employees WHERE manager_id = :m"), {"m": user.emp_id})]
        return [user.emp_id, *ids]
    return [user.emp_id]
