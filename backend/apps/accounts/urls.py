from django.urls import path

from . import api

urlpatterns = [
    path("register/", api.RegisterView.as_view()),
    path("login/", api.LoginView.as_view()),
    path("logout/", api.LogoutView.as_view()),
    path("me/", api.MeView.as_view()),
    path("verify-email/", api.VerifyEmailView.as_view()),
    path("resend-verification/", api.ResendVerificationView.as_view()),
    path("forgot-password/", api.ForgotPasswordView.as_view()),
    path("reset-password/", api.ResetPasswordView.as_view()),
    path("change-password/", api.ChangePasswordView.as_view()),
    path("service-token/", api.ServiceTokenView.as_view()),
    path("csrf/", api.CsrfView.as_view()),
]
