"""Authentication business logic: registration, verification, reset, login with lockout."""
import hashlib
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import login, logout
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit import services as audit
from apps.common import roles as R
from apps.common.exceptions import ServiceError
from apps.notifications.services import send_email_safe

from .models import EmailVerificationToken, PasswordResetToken, User

logger = logging.getLogger("dayflow.auth")


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


def issue_token(user, model, hours: int) -> str:
    raw = secrets.token_urlsafe(32)
    model.objects.filter(user=user, used=False).update(used=True)
    model.objects.create(user=user, token_hash=_hash(raw), expires_at=timezone.now() + timedelta(hours=hours))
    return raw


def consume_token(raw: str, model) -> User:
    tok = model.objects.select_related("user").filter(token_hash=_hash(raw or ""), used=False).first()
    if not tok or tok.expires_at < timezone.now():
        raise ServiceError("This link is invalid or has expired.", 400)
    tok.used = True
    tok.save(update_fields=["used"])
    return tok.user


def check_password_strength(password: str, user=None):
    try:
        validate_password(password, user)
    except DjangoValidationError as e:
        raise ServiceError("Weak password", 400, {"password": list(e.messages)})


def send_verification_email(user):
    raw = issue_token(user, EmailVerificationToken, settings.VERIFY_TOKEN_HOURS)
    link = f"{settings.SITE_URL}/verify-email/{raw}/"
    send_email_safe(user.email, "Verify your Dayflow account",
                    f"Welcome to Dayflow HRMS!\n\nVerify your email: {link}\n\nThis link expires in {settings.VERIFY_TOKEN_HOURS} hours.")
    return raw


def register_public(request, *, employee_id, first_name, last_name, email, phone, password):
    """Public sign-up. ALWAYS creates an EMPLOYEE - privileged roles are never self-assignable."""
    from apps.employees.services import create_employee
    check_password_strength(password)
    emp = create_employee(request=request, employee_id=employee_id, email=email, first_name=first_name,
                          last_name=last_name, phone=phone, password=password, role=R.EMPLOYEE,
                          email_verified=not settings.REQUIRE_EMAIL_VERIFICATION)   # atomic internally
    if settings.REQUIRE_EMAIL_VERIFICATION:
        send_verification_email(emp.user)    # sent only after the account is committed
    return emp


def verify_email(raw: str) -> User:
    user = consume_token(raw, EmailVerificationToken)
    user.email_verified = True
    user.save(update_fields=["email_verified", "updated_at"])
    return user


def request_password_reset(email: str):
    """Always silent about whether the account exists (prevents enumeration)."""
    user = User.objects.filter(email__iexact=email, is_active=True).first()
    if user:
        raw = issue_token(user, PasswordResetToken, settings.RESET_TOKEN_HOURS)
        send_email_safe(user.email, "Reset your Dayflow password",
                        f"Reset your password: {settings.SITE_URL}/reset-password/{raw}/\n\nExpires in {settings.RESET_TOKEN_HOURS} hour(s).")


def reset_password(request, raw: str, password: str):
    check_password_strength(password)
    user = consume_token(raw, PasswordResetToken)
    user.set_password(password)
    user.failed_login_attempts, user.locked_until = 0, None
    user.save()
    audit.log(request, "PASSWORD_RESET", "User", user.pk, user=user)
    return user


def login_user(request, email: str, password: str) -> User:
    user = User.objects.filter(email__iexact=(email or "").strip()).first()
    now = timezone.now()
    if user and user.locked_until and user.locked_until > now:
        raise ServiceError("Account temporarily locked after too many failed attempts. Try again later.", 429)
    if not user or not user.check_password(password or ""):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.MAX_FAILED_LOGINS:
                user.locked_until = now + timedelta(minutes=settings.LOCKOUT_MINUTES)
                user.failed_login_attempts = 0
                logger.warning("Account locked: %s", user.email)
            user.save(update_fields=["failed_login_attempts", "locked_until"])
        audit.log(request, "LOGIN_FAILED", "User", getattr(user, "pk", ""), new={"email": email})
        raise ServiceError("Invalid email or password.", 401)
    if not user.is_active:
        raise ServiceError("This account has been deactivated. Contact HR.", 403)
    if settings.REQUIRE_EMAIL_VERIFICATION and not user.email_verified:
        raise ServiceError("Please verify your email before signing in.", 403, {"code": "email_not_verified"})
    user.failed_login_attempts, user.locked_until = 0, None
    user.save(update_fields=["failed_login_attempts", "locked_until"])
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    return user


def logout_user(request):
    logout(request)
