from django.contrib import admin

from .models import Department, Designation, Employee

admin.site.register(Department)
admin.site.register(Designation)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_id", "first_name", "last_name", "department", "designation")
    search_fields = ("employee_id", "first_name", "last_name")
