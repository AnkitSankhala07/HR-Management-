from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.common import roles as R
from apps.common.files import validate_upload

from .models import Department, Designation, Employee

User = get_user_model()


class DepartmentSerializer(serializers.ModelSerializer):
    employee_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Department
        fields = ["id", "name", "description", "employee_count"]


class DesignationSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)

    class Meta:
        model = Designation
        fields = ["id", "title", "department", "department_name"]


class EmployeeSerializer(serializers.ModelSerializer):
    """Read serializer. Contains NO salary data (payroll is a separate, restricted resource)."""
    email = serializers.EmailField(source="user.email", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)
    is_active = serializers.BooleanField(source="user.is_active", read_only=True)
    full_name = serializers.CharField(read_only=True)
    department_name = serializers.CharField(source="department.name", read_only=True, default=None)
    designation_title = serializers.CharField(source="designation.title", read_only=True, default=None)
    manager_name = serializers.CharField(source="manager.full_name", read_only=True, default=None)
    photo = serializers.SerializerMethodField()

    class Meta:
        model = Employee
        fields = ["id", "employee_id", "first_name", "last_name", "full_name", "email", "role", "is_active", "phone",
                  "address", "city", "state", "date_of_birth", "department", "department_name", "designation",
                  "designation_title", "manager", "manager_name", "joining_date", "employment_type", "photo"]

    def get_photo(self, obj):
        return obj.profile_picture.url if obj.profile_picture else None


class EmployeeSelfSerializer(serializers.ModelSerializer):
    """Fields an employee may edit about themself."""
    class Meta:
        model = Employee
        fields = ["phone", "address", "city", "state", "date_of_birth", "profile_picture"]

    def validate_profile_picture(self, f):
        if f:
            validate_upload(f, allowed=("png", "jpg", "jpeg"))
        return f


class EmployeeWriteSerializer(serializers.ModelSerializer):
    """HR create/update. Role/email/employee_id are handled in the service/view."""
    email = serializers.EmailField(write_only=True, required=False)
    role = serializers.ChoiceField(choices=R.ROLE_CHOICES, write_only=True, required=False)
    password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Employee
        fields = ["employee_id", "first_name", "last_name", "email", "role", "password", "phone", "address", "city",
                  "state", "date_of_birth", "department", "designation", "manager", "joining_date", "employment_type",
                  "profile_picture"]
        extra_kwargs = {"employee_id": {"required": False}, "joining_date": {"required": False}}

    def validate_profile_picture(self, f):
        if f:
            validate_upload(f, allowed=("png", "jpg", "jpeg"))
        return f
