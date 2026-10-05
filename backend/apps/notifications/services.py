"""Database-backed notifications + optional email (never crashes when SMTP is missing)."""
import logging

from django.conf import settings
from django.core.mail import send_mail

from .models import Notification

logger = logging.getLogger("dayflow.notify")


def send_email_safe(to: str, subject: str, body: str) -> bool:
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=False)
        return True
    except Exception:
        logger.warning("Email to %s failed (SMTP not configured?)", to, exc_info=settings.DEBUG)
        return False


def notify(user, title: str, message: str, ntype: str = "SYSTEM", link: str = "", email: bool = False):
    if user is None:
        return None
    n = Notification.objects.create(user=user, title=title, message=message, notification_type=ntype, link=link)
    if email and user.email:
        send_email_safe(user.email, f"[Dayflow] {title}", message)
    return n


def notify_roles(roles, title, message, ntype="SYSTEM", link="", email=False, exclude=None):
    from django.contrib.auth import get_user_model
    qs = get_user_model().objects.filter(role__in=roles, is_active=True)
    if exclude:
        qs = qs.exclude(pk=exclude.pk)
    for u in qs:
        notify(u, title, message, ntype, link, email)
