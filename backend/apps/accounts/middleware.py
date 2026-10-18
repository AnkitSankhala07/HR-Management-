"""
MultiAccountMiddleware:
Allows maintaining multiple active authenticated user accounts within the same browser session.
Resolves request.user based on URL parameter (?as=... / ?account=...), request header (X-Dayflow-Account),
or cookie, falling back to the session's active account.
Synchronizes session user ID and auth hash to prevent Django AuthenticationMiddleware session flushing.
"""
from django.contrib.auth import get_user_model

User = get_user_model()


class MultiAccountMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if hasattr(request, "session"):
            multi_ids = list(request.session.get("_multi_accounts", []))

            # Ensure current authenticated user is recorded
            if getattr(request, "user", None) and request.user.is_authenticated:
                if request.user.pk not in multi_ids:
                    multi_ids.append(request.user.pk)
                    request.session["_multi_accounts"] = multi_ids
                    request.session.modified = True

            # Check if a specific account is requested for this tab / request
            target_val = (
                request.GET.get("as")
                or request.GET.get("account")
                or request.headers.get("X-Dayflow-Account")
                or request.headers.get("X-Dayflow-User")
                or request.COOKIES.get("dayflow_active_account")
            )

            target_user = None
            if target_val and multi_ids:
                target_str = str(target_val).strip()
                if target_str.isdigit() and int(target_str) in multi_ids:
                    target_user = User.objects.filter(pk=int(target_str), is_active=True).first()
                elif "@" in target_str:
                    matched = User.objects.filter(email__iexact=target_str, is_active=True).first()
                    if matched and matched.pk in multi_ids:
                        target_user = matched

            if target_user:
                request.user = target_user
                # Keep session auth hash in sync with target user
                request.session["_active_account_id"] = target_user.pk
                request.session["_auth_user_id"] = str(target_user.pk)
                request.session["_auth_user_hash"] = target_user.get_session_auth_hash()
                request.session.modified = True

            # Populate request.multi_accounts with all authenticated user objects
            if multi_ids:
                users_qs = User.objects.filter(pk__in=multi_ids, is_active=True).select_related("employee")
                user_map = {u.pk: u for u in users_qs}
                request.multi_accounts = [user_map[uid] for uid in multi_ids if uid in user_map]
            else:
                request.multi_accounts = [request.user] if (getattr(request, "user", None) and request.user.is_authenticated) else []
        else:
            request.multi_accounts = []

        response = self.get_response(request)
        return response
