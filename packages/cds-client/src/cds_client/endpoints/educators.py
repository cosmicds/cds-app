from ..exceptions import CDSNotFoundError
from ..models.base import Classroom, Educator, EducatorCreated, EducatorCreationInfo
from .base import BaseEndpoint


class EducatorsEndpoint(BaseEndpoint):
    """Endpoints under ``/educators``."""

    def get(self, identifier: str | int) -> Educator | None:
        """Fetch an educator by username (string) or numeric ID.

        Returns ``None`` if no educator with that identifier exists.
        """
        try:
            data = self._session.get(f"/educators/{identifier}").json()
        except CDSNotFoundError:
            return None
        return Educator(**data["educator"]) if data.get("educator") else None

    def get_all(self) -> list[Educator]:
        """Return all educators."""
        data = self._session.get("/educators").json()
        return [Educator(**e) for e in data]

    def create(self, info: EducatorCreationInfo) -> EducatorCreated:
        """Create a new educator account."""
        data = self._session.post(
            "/educators/create", json=info.model_dump(exclude_none=True)
        ).json()
        return EducatorCreated(
            educator_info=data.get("educator_info"),
            status=data["status"],
            success=data["success"],
        )

    def get_classes(self, educator_id: int) -> list[Classroom]:
        """Return the classes managed by an educator."""
        data = self._session.get(f"/educator-classes/{educator_id}").json()
        return [Classroom(**c) for c in data.get("classes", [])]
