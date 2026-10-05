from .base import *  # noqa

DEBUG = env_bool("DEBUG", True)
ALLOWED_HOSTS = ["*"]
REQUIRE_EMAIL_VERIFICATION = env_bool("REQUIRE_EMAIL_VERIFICATION", True)
