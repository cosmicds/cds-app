"""Signed cookie utilities for bridging student sessions from portal to stories."""

import os

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

_HANDSHAKE_SALT = "cds-student-handshake"
_SESSION_SALT = "cds-student-session"
_SESSION_MAX_AGE = 30 * 24 * 60 * 60  # 30 days


def _serializer(salt: str) -> URLSafeTimedSerializer:
    secret = os.environ.get("CDS_STUDENT_SECRET") or os.environ.get("SOLARA_SESSION_SECRET_KEY", "")
    return URLSafeTimedSerializer(secret, salt=salt)


def sign_student_token(username: str) -> str:
    """Short-lived (60 s) token for the portal → /student-auth handshake."""
    return _serializer(_HANDSHAKE_SALT).dumps(username)


def verify_student_token(token: str, max_age: int = 60) -> str | None:
    """Return the username embedded in *token*, or None if invalid/expired."""
    try:
        return _serializer(_HANDSHAKE_SALT).loads(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None


def make_student_cookie(username: str) -> str:
    """Long-lived signed value stored as the ``cds_student`` cookie."""
    return _serializer(_SESSION_SALT).dumps(username)


def verify_student_cookie(value: str, max_age: int = _SESSION_MAX_AGE) -> str | None:
    """Return the username embedded in the cookie value, or None if invalid/expired."""
    try:
        return _serializer(_SESSION_SALT).loads(value, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return None
