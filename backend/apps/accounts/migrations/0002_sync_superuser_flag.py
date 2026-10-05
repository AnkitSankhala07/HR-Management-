# Generated manually to sync superuser flag with role
from django.db import migrations


def sync_superuser_flags(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="SUPER_ADMIN").update(is_superuser=True)
    User.objects.exclude(role="SUPER_ADMIN").update(is_superuser=False)


def reverse_sync(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(sync_superuser_flags, reverse_code=reverse_sync),
    ]
