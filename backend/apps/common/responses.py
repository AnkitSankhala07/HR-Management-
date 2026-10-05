from rest_framework.response import Response


def ok(data=None, message: str = "OK", status: int = 200) -> Response:
    return Response({"success": True, "message": message, "data": data if data is not None else {}}, status=status)
