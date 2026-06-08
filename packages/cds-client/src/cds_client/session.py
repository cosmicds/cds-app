"""HTTP session wrapper providing auth and base-URL handling."""

import os
from functools import cached_property

from requests import Response, Session

from .exceptions import CDSAPIError, CDSAuthError, CDSNotFoundError, CDSConflictError


class CDSSession:
    """Authenticated HTTP session for the CosmicDS API.

    Parameters
    ----------
    api_key : str, optional
        API key sent as the ``Authorization`` header.  Defaults to the
        ``CDS_API_KEY`` environment variable.
    base_url : str, optional
        Override the default API base URL.
    prefix : str, optional
        Optional path prefix appended to ``base_url`` (e.g. ``/hubbles_law``).
    """

    DEFAULT_BASE_URL = "https://api.cosmicds.cfa.harvard.edu"

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        prefix: str = "",
    ):
        self._api_key = api_key
        self._base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self._prefix = prefix.rstrip("/")

    @cached_property
    def _session(self) -> Session:
        session = Session()
        key = self._api_key or os.getenv("CDS_API_KEY", "")
        session.headers.update({"Authorization": key})
        return session

    def _url(self, path: str) -> str:
        return f"{self._base_url}{self._prefix}{path}"

    def _check(self, r: Response) -> Response:
        if r.status_code in (401, 403):
            raise CDSAuthError(r.status_code, r.text)
        if r.status_code == 404:
            raise CDSNotFoundError(r.status_code, r.text)
        if r.status_code == 409:
            raise CDSConflictError(r.status_code, r.text)
        if r.status_code >= 400:
            raise CDSAPIError(r.status_code, r.text)
        return r

    def get(self, path: str, **kwargs) -> Response:
        return self._check(self._session.get(self._url(path), **kwargs))

    def post(self, path: str, **kwargs) -> Response:
        return self._check(self._session.post(self._url(path), **kwargs))

    def put(self, path: str, **kwargs) -> Response:
        return self._check(self._session.put(self._url(path), **kwargs))

    def patch(self, path: str, **kwargs) -> Response:
        return self._check(self._session.patch(self._url(path), **kwargs))

    def delete(self, path: str, **kwargs) -> Response:
        return self._check(self._session.delete(self._url(path), **kwargs))

    def with_prefix(self, prefix: str) -> "CDSSession":
        """Return a new session sharing the same underlying connection but with a path prefix."""
        new = CDSSession.__new__(CDSSession)
        new._api_key = self._api_key
        new._base_url = self._base_url
        new._prefix = prefix.rstrip("/")
        # Share the underlying requests.Session so auth headers are reused
        new.__dict__["_session"] = self._session
        return new
