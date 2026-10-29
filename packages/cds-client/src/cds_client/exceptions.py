class CDSAPIError(Exception):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"API error {status_code}: {message}")


class CDSNotFoundError(CDSAPIError):
    """Raised on 404 responses."""


class CDSAuthError(CDSAPIError):
    """Raised on 401/403 responses."""


class CDSConflictError(CDSAPIError):
    """Raised on 409 responses (e.g. resource already exists)."""
