"""Audit trail helper. Never logs secrets (passwords/tokens are stripped)."""
import logging

from .models import AuditLog

logger = logging.getLogger("dayflow.audit")
SENSITIVE = {"password", "token", "temp_password", "password_hash"}


def _clean(d):
    if isinstance(d, dict):
        return {k: ("***" if k in SENSITIVE else _clean(v)) for k, v in d.items()}
    return d


def client_ip(request):
    if request is None:
        return None
    fwd = request.META.get("HTTP_X_FORWARDED_FOR")
    return (fwd.split(",")[0].strip() if fwd else request.META.get("REMOTE_ADDR")) or None


def log(request, action: str, entity: str, entity_id="", old=None, new=None, user=None):
    user = user or (getattr(request, "user", None) if request is not None else None)
    if user is not None and not getattr(user, "is_authenticated", False):
        user = None
    try:
        AuditLog.objects.create(
            user=user, user_email=getattr(user, "email", ""), action=action, entity=entity, entity_id=str(entity_id),
            ip_address=client_ip(request),
            user_agent=(request.META.get("HTTP_USER_AGENT", "")[:300] if request is not None else ""),
            old_value=_clean(old), new_value=_clean(new),
        )
    except Exception:  # auditing must never break a business action
        logger.exception("Failed to write audit log")
    logger.info("AUDIT %s %s#%s by %s", action, entity, entity_id, getattr(user, "email", "system"))
