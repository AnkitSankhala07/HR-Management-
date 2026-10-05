import re

from django.core.exceptions import ValidationError


class ComplexityValidator:
    """Require upper, lower, digit and special character."""

    def validate(self, password, user=None):
        checks = [(r"[A-Z]", "an uppercase letter"), (r"[a-z]", "a lowercase letter"),
                  (r"\d", "a digit"), (r"[^A-Za-z0-9]", "a special character")]
        missing = [label for rx, label in checks if not re.search(rx, password)]
        if missing:
            raise ValidationError("Password must contain " + ", ".join(missing) + ".", code="weak_password")

    def get_help_text(self):
        return "Use upper & lower case letters, a digit and a special character."
