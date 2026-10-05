import time

import jwt
from django.conf import settings
from django.middleware.csrf import get_token
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

from apps.common.exceptions import ServiceError
from apps.common.responses import ok

from . import services


class RegisterSerializer(serializers.Serializer):
    employee_id = serializers.RegexField(r"^[A-Za-z0-9-]{3,20}$", error_messages={"invalid": "3-20 letters, digits or dashes."})
    first_name = serializers.CharField(max_length=60)
    last_name = serializers.CharField(max_length=60)
    email = serializers.EmailField()
    phone = serializers.RegexField(r"^\+?[0-9 -]{7,15}$", required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, d):
        if d["password"] != d.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return d


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField()


def user_payload(user):
    emp = getattr(user, "employee", None)
    return {"id": user.pk, "email": user.email, "employee_id": user.employee_id, "role": user.role,
            "name": emp.full_name if emp else user.email, "email_verified": user.email_verified}


class ScopedAPIView(APIView):
    permission_classes = [AllowAny]


class RegisterView(ScopedAPIView):
    throttle_scope = "register"

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        services.register_public(request, **s.validated_data)
        msg = "Account created. Check your email to verify your account." if settings.REQUIRE_EMAIL_VERIFICATION else "Account created. You can sign in."
        return ok({}, msg, 201)


class LoginView(ScopedAPIView):
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = services.login_user(request, **s.validated_data)
        return ok({"user": user_payload(user), "redirect": "/dashboard/"}, "Signed in")


class LogoutView(APIView):
    def post(self, request):
        services.logout_user(request)
        return ok({}, "Signed out")


class MeView(APIView):
    def get(self, request):
        return ok(user_payload(request.user))


class VerifyEmailView(ScopedAPIView):
    def post(self, request):
        services.verify_email(request.data.get("token", ""))
        return ok({}, "Email verified. You can now sign in.")


class ResendVerificationView(ScopedAPIView):
    throttle_scope = "password"

    def post(self, request):
        from .models import User
        u = User.objects.filter(email__iexact=request.data.get("email", ""), email_verified=False, is_active=True).first()
        if u:
            services.send_verification_email(u)
        return ok({}, "If the account exists and is unverified, a new link has been sent.")


class ForgotPasswordView(ScopedAPIView):
    throttle_scope = "password"

    def post(self, request):
        services.request_password_reset(request.data.get("email", ""))
        return ok({}, "If that email is registered, a reset link has been sent.")


class ResetPasswordView(ScopedAPIView):
    throttle_scope = "password"

    def post(self, request):
        d = request.data
        if d.get("password") != d.get("confirm_password"):
            raise ServiceError("Passwords do not match.", 400, {"confirm_password": "Passwords do not match."})
        services.reset_password(request, d.get("token", ""), d.get("password", ""))
        return ok({}, "Password updated. You can now sign in.")


class ChangePasswordView(APIView):
    def post(self, request):
        d = request.data
        if not request.user.check_password(d.get("current_password", "")):
            raise ServiceError("Current password is incorrect.", 400)
        services.check_password_strength(d.get("password", ""), request.user)
        request.user.set_password(d["password"])
        request.user.save()
        from django.contrib.auth import update_session_auth_hash
        update_session_auth_hash(request, request.user)
        return ok({}, "Password changed")


class ServiceTokenView(APIView):
    """Short-lived signed JWT so the browser can call the FastAPI service as this user.
    FastAPI re-verifies the user/role in MySQL on every request (the token carries identity, not trust)."""

    def get(self, request):
        now = int(time.time())
        payload = {"sub": str(request.user.pk), "role": request.user.role, "iat": now,
                   "exp": now + int(settings.SERVICE_JWT_TTL.total_seconds()), "iss": "dayflow-django"}
        token = jwt.encode(payload, settings.SERVICE_JWT_SECRET, algorithm="HS256")
        return ok({"token": token, "fastapi_url": settings.FASTAPI_PUBLIC_URL, "expires_in": payload["exp"] - now})


class CsrfView(ScopedAPIView):
    def get(self, request):
        return ok({"csrf": get_token(request)})


# ---- OpenAPI documentation for the plain APIViews
for _cls, _req in ((RegisterView, RegisterSerializer), (LoginView, LoginSerializer)):
    extend_schema(request=_req, responses=OpenApiTypes.OBJECT, tags=["Authentication"])(_cls)
for _cls in (LogoutView, MeView, VerifyEmailView, ResendVerificationView, ForgotPasswordView, ResetPasswordView, ChangePasswordView, ServiceTokenView, CsrfView):
    extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT, tags=["Authentication"])(_cls)
