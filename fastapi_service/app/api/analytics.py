from fastapi import APIRouter, Depends
from sqlalchemy.engine import Connection

from ..analytics import queries as q
from ..dependencies import HR, PAYROLL, RECRUITMENT, CurrentUser, get_conn, require, visible_employee_ids

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/workforce", summary="Company-wide workforce KPIs (HR only)")
def workforce(user: CurrentUser = Depends(require(*HR)), conn: Connection = Depends(get_conn)):
    return q.workforce(conn)


@router.get("/attendance", summary="Attendance trend & split (HR: all, Manager: team)")
def attendance(user: CurrentUser = Depends(require(*HR, "MANAGER")), conn: Connection = Depends(get_conn)):
    return q.attendance(conn, visible_employee_ids(conn, user))


@router.get("/leave", summary="Leave trend & types (HR: all, Manager: team)")
def leave(user: CurrentUser = Depends(require(*HR, "MANAGER")), conn: Connection = Depends(get_conn)):
    return q.leave(conn, visible_employee_ids(conn, user))


@router.get("/payroll", summary="Payroll analytics (Super Admin / HR Admin only)")
def payroll(user: CurrentUser = Depends(require(*PAYROLL)), conn: Connection = Depends(get_conn)):
    return q.payroll(conn)


@router.get("/recruitment", summary="Hiring funnel (HR & recruiters)")
def recruitment(user: CurrentUser = Depends(require(*RECRUITMENT)), conn: Connection = Depends(get_conn)):
    return q.recruitment(conn)


@router.get("/skills", summary="Skill distribution & gaps (HR: all, Manager: team)")
def skills(user: CurrentUser = Depends(require(*HR, "MANAGER")), conn: Connection = Depends(get_conn)):
    return q.skills(conn, visible_employee_ids(conn, user))
