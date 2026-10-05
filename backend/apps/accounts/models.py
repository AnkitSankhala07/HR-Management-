from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models

from apps.common import roles as R


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("role", R.SUPER_ADMIN)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verified", True)
        return self.create_user(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    employee_id = models.CharField(max_length=20, unique=True)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=R.ROLE_CHOICES, default=R.EMPLOYEE, db_index=True)
    email_verified = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["employee_id"]

    class Meta:
        db_table = "users"

    @property
    def is_staff(self) -> bool:  # Django admin access: Super Admin only
        return self.role == R.SUPER_ADMIN or self.is_superuser

    def save(self, *args, **kwargs):
        self.is_superuser = (self.role == R.SUPER_ADMIN)
        if "update_fields" in kwargs and kwargs["update_fields"] is not None:
            kwargs["update_fields"] = set(kwargs["update_fields"]) | {"is_superuser"}
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.email} ({self.role})"


class _Token(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    token_hash = models.CharField(max_length=64, unique=True)   # only the SHA-256 is stored
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class EmailVerificationToken(_Token):
    class Meta:
        db_table = "email_verification_tokens"


class PasswordResetToken(_Token):
    class Meta:
        db_table = "password_reset_tokens"
