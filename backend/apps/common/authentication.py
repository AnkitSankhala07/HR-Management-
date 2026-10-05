"""Custom authentication classes for Dayflow HRMS."""
from rest_framework.authentication import SessionAuthentication as BaseSessionAuthentication


class SessionAuthentication(BaseSessionAuthentication):
    """SessionAuthentication that returns an authenticate header.

    When an unauthenticated request hits an endpoint requiring authentication,
    DRF checks whether authenticators provided an authenticate_header. By returning
    a valid header scheme ("Session"), unauthenticated requests produce HTTP 401 Unauthorized
    instead of defaulting to HTTP 403 Forbidden.
    """

    def authenticate_header(self, request):
        return "Session"
