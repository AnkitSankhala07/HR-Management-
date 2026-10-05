"""Secure upload validation: size, extension, filename, and magic-byte MIME sniffing."""
import os
import re
import uuid

from django.conf import settings
from rest_framework.exceptions import ValidationError

SIGNATURES = {
    "pdf": (b"%PDF-", "application/pdf"),
    "png": (b"\x89PNG\r\n\x1a\n", "image/png"),
    "jpg": (b"\xff\xd8\xff", "image/jpeg"),
    "jpeg": (b"\xff\xd8\xff", "image/jpeg"),
}
BLOCKED = {"exe", "sh", "bat", "cmd", "js", "py", "php", "html", "svg", "dll", "com", "msi", "jar"}


def safe_name(name: str) -> str:
    base = os.path.basename(name.replace("\\", "/"))
    stem, _, ext = base.rpartition(".")
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", stem or base)[:80] or "file"
    return f"{stem}.{ext.lower()}" if stem and ext and stem != base else stem


def validate_upload(f, allowed=("pdf", "png", "jpg", "jpeg")):
    """Validate and rename an UploadedFile. Returns the mime type detected from content."""
    if f.size > settings.MAX_UPLOAD_BYTES:
        raise ValidationError({"file": f"File too large (max {settings.MAX_UPLOAD_BYTES // 1024 // 1024} MB)."})
    name = os.path.basename((f.name or "").replace("\\", "/"))
    if ".." in name or "\x00" in name:
        raise ValidationError({"file": "Invalid filename."})
    parts = name.lower().split(".")
    if len(parts) < 2 or any(p in BLOCKED for p in parts[1:]):
        raise ValidationError({"file": "File type not allowed."})
    ext = parts[-1]
    if ext not in allowed:
        raise ValidationError({"file": f"Allowed types: {', '.join(allowed)}."})
    head = f.read(16)
    f.seek(0)
    magic, mime = SIGNATURES[ext]
    if not head.startswith(magic):
        raise ValidationError({"file": "File content does not match its extension."})
    claimed = getattr(f, "content_type", None)
    if claimed and claimed != mime and not (mime == "image/jpeg" and claimed == "image/jpg"):
        raise ValidationError({"file": "File MIME type mismatch."})
    f.name = f"{uuid.uuid4().hex}.{ext}"   # never keep user-controlled storage names
    return mime
