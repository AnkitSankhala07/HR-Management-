from django.contrib import admin

from .models import User


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "employee_id", "role", "email_verified", "is_active")
    list_filter = ("role", "is_active", "email_verified")
    search_fields = ("email", "employee_id")
    exclude = ("password",)
