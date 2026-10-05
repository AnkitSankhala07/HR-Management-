from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver

from apps.audit import services as audit


@receiver(user_logged_in)
def _in(sender, request, user, **kw):
    audit.log(request, "LOGIN", "User", user.pk, user=user)


@receiver(user_logged_out)
def _out(sender, request, user, **kw):
    if user:
        audit.log(request, "LOGOUT", "User", user.pk, user=user)
