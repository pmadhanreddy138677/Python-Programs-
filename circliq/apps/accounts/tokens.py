from django.conf import settings
from django.core import signing

SALT = "circliq-email-verify"


def make_token(user):
    return signing.dumps({"uid": user.pk, "email": user.email}, salt=SALT)


def read_token(token):
    """Return the payload dict, or None if invalid/expired."""
    try:
        return signing.loads(token, salt=SALT, max_age=settings.EMAIL_VERIFICATION_MAX_AGE)
    except signing.BadSignature:
        return None
