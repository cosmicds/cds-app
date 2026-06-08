from ..exceptions import CDSNotFoundError
from ..models.base import Classroom, Student, StudentCreated, StudentCreationInfo
from .base import BaseEndpoint


class StudentsEndpoint(BaseEndpoint):
    """Endpoints under ``/students`` and ``/student``."""

    def get(self, identifier: str | int) -> Student | None:
        """Fetch a student by username (string) or numeric ID.

        Returns ``None`` if no student with that identifier exists.
        """
        try:
            data = self._session.get(f"/students/{identifier}").json()
        except CDSNotFoundError:
            return None
        return Student(**data["student"]) if data.get("student") else None

    def get_all(self) -> list[Student]:
        """Return all students."""
        data = self._session.get("/students").json()
        return [Student(**s) for s in data]

    def create(self, info: StudentCreationInfo) -> StudentCreated:
        """Create a new student account."""
        data = self._session.post(
            "/students/create", json=info.model_dump(exclude_none=True)
        ).json()
        return StudentCreated(status=data["status"], success=data["success"])

    def get_classes(self, identifier: str | int) -> list[Classroom]:
        """Return the classes a student is enrolled in."""
        data = self._session.get(f"/students/{identifier}/classes").json()
        return [Classroom(**c) for c in data.get("classes", [])]

    def remove_from_class(self, identifier: str | int, class_id: int) -> None:
        """Remove a student from a specific class."""
        self._session.delete(f"/students/{identifier}/classes/{class_id}")

    def ignore_for_story(
        self,
        identifier: str | int,
        story_name: str,
        ignore: bool = True,
    ) -> None:
        """Set the ignored flag for a student on a given story."""
        self._session.put(
            f"/students/ignore/{identifier}/{story_name}",
            json={"ignore": ignore},
        )
