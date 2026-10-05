"""Centralised error handling producing the {success, message, errors} envelope."""
import logging

from django.core.exceptions import PermissionDenied, ValidationError as DjangoValidationError
from django.http import Http404
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger("dayflow.api")


class ServiceError(Exception):
    """Raised by the service layer; mapped to an HTTP response by views."""

    def __init__(self, message: str, status_code: int = 400, errors: dict | None = None):
        super().__init__(message)
        self.message, self.status_code, self.errors = message, status_code, errors or {}


def api_exception_handler(exc, context):
    if isinstance(exc, ServiceError):
        return Response({"success": False, "message": exc.message, "errors": exc.errors}, status=exc.status_code)
    if isinstance(exc, DjangoValidationError):
        exc = exceptions.ValidationError(exc.message_dict if hasattr(exc, "error_dict") else exc.messages)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound()
    if isinstance(exc, PermissionDenied):
        exc = exceptions.PermissionDenied()
    response = exception_handler(exc, context)
    if response is None:
        logger.exception("Unhandled API error", exc_info=exc)
        return Response({"success": False, "message": "Internal server error", "errors": {}},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    data = response.data
    if response.status_code == 400 and isinstance(data, (dict, list)):
        message, errors = "Validation failed", data if isinstance(data, dict) else {"non_field_errors": data}
    else:
        message = data.get("detail", "Error") if isinstance(data, dict) else str(data)
        errors = {} if isinstance(data, dict) and "detail" in data else data
    response.data = {"success": False, "message": str(message), "errors": errors}
    return response
