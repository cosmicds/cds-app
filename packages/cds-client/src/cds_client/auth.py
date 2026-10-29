"""Utilities for hashing user identifiers for the CosmicDS API."""

import hashlib
import os


def hash_user(user_ref: str, secret_key: str | None = None) -> str:
    """Hash a user identifier (email or name) for API requests.

    Parameters
    ----------
    user_ref : str
        The user's email or display name.
    secret_key : str, optional
        The session secret. Defaults to the
        ``SOLARA_SESSION_SECRET_KEY`` environment variable.

    Returns
    -------
    str
        A hex-encoded SHA-1 hash used as the API username.
    """
    secret = secret_key or os.environ.get("SOLARA_SESSION_SECRET_KEY", "")
    return hashlib.sha1((user_ref + secret).encode()).hexdigest()


def get_hashed_user(secret_key: str | None = None) -> str | None:
    """Derive the hashed user identifier from the active Solara auth session.

    Requires ``solara-enterprise`` to be installed and a user to be logged in.

    Parameters
    ----------
    secret_key : str, optional
        Override for ``SOLARA_SESSION_SECRET_KEY``.

    Returns
    -------
    str or None
        The hashed user string, or ``None`` if auth is unavailable/unauthenticated.
    """
    try:
        from solara_enterprise import auth  # type: ignore[import]
    except ImportError:
        return None

    if auth.user.value is None:
        return None

    userinfo = auth.user.value.get("userinfo", {})
    user_ref = userinfo.get("cds/email") or userinfo.get("cds/name")
    if not user_ref:
        return None

    return hash_user(user_ref, secret_key)
