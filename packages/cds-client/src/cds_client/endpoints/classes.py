from ..exceptions import CDSNotFoundError
from ..models.base import Classroom, ClassCreationInfo, Student
from .base import BaseEndpoint


class ClassesEndpoint(BaseEndpoint):
    """Endpoints under ``/classes``."""

    def get(self, identifier: str | int) -> Classroom | None:
        """Fetch a class by code (string) or numeric ID."""
        try:
            data = self._session.get(f"/classes/{identifier}").json()
        except CDSNotFoundError:
            return None
        inner = data.get("class") if data else None
        return Classroom(**inner) if inner else None

    def create(self, info: ClassCreationInfo) -> Classroom:
        """Create a new class."""
        data = self._session.post(
            "/classes/create", json=info.model_dump(exclude_none=True)
        ).json()
        # The create endpoint returns a partial object; fetch the full record by code.
        code = data["class_info"]["code"]
        classroom = self.get(code)
        if classroom is None:
            raise RuntimeError(f"Class '{code}' was created but could not be fetched.")
        return classroom

    def delete(self, identifier: str | int) -> None:
        """Delete a class by code or ID."""
        self._session.delete(f"/classes/{identifier}")

    def get_size(self, class_id: int) -> int:
        """Return the current enrolment count for a class."""
        return self._session.get(f"/classes/size/{class_id}").json()["size"]

    def get_expected_size(self, class_id: int) -> int:
        """Return the expected enrolment size for a class."""
        return self._session.get(f"/classes/expected-size/{class_id}").json()["expected_size"]

    def get_roster(self, class_id: int) -> list[Student]:
        """Return all students enrolled in a class."""
        data = self._session.get(f"/classes/roster/{class_id}").json()
        return [Student(**s) for s in data]

    def join(self, username: str, class_code: str) -> Classroom:
        """Add a student to a class by class code."""
        data = self._session.post(
            "/classes/join", json={"username": username, "class_code": class_code}
        ).json()
        return Classroom(**data)

    def get_active(self, class_id: int, story_name: str) -> bool:
        """Return whether a class is active for a given story."""
        data = self._session.get(f"/classes/active/{class_id}/{story_name}").json()
        return data["active"]

    def set_active(self, class_id: int, story_name: str, active: bool) -> bool:
        """Set the active status of a class for a given story."""
        data = self._session.post(
            f"/classes/active/{class_id}/{story_name}",
            json={"active": active},
        ).json()
        return data.get("success", False)

    def validate_code(self, class_code: str) -> bool:
        """Return ``True`` if a class with the given code exists."""
        return self.get(class_code) is not None

    def get_roster_info(self, class_id: int, story_name: str) -> dict:
        """Return roster info for a class and story."""
        return self._session.get(f"/roster-info/{class_id}/{story_name}").json()
