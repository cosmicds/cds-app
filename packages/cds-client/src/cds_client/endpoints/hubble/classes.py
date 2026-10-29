from ...exceptions import CDSNotFoundError
from ..base import BaseEndpoint


class HubbleClassesEndpoint(BaseEndpoint):
    """Hubble's Law class-management endpoints."""

    # Waiting room override
    def get_waiting_room_override(self, class_id: int) -> bool:
        """Return whether the waiting-room override is active for a class."""
        try:
            data = self._session.get(f"/waiting-room-override/{class_id}").json()
        except CDSNotFoundError:
            return False
        return data.get("override_status", False)

    def set_waiting_room_override(self, class_id: int) -> None:
        """Enable the waiting-room override for a class."""
        self._session.put("/waiting-room-override", json={"class_id": class_id})

    def delete_waiting_room_override(self, class_id: int) -> None:
        """Disable the waiting-room override for a class."""
        self._session.delete("/waiting-room-override", json={"class_id": class_id})

    # Student merging
    def merge_students(self, class_id: int, desired_merge_count: int) -> dict:
        """Merge student data within a class."""
        return self._session.put(
            "/merge-students",
            json={"class_id": class_id, "desired_merge_count": desired_merge_count},
        ).json()

    def get_merged_students(self, class_id: int, full: bool = False) -> list[dict]:
        """Return students that have been merged within a class."""
        data = self._session.get(
            f"/merge-students/{class_id}", params={"full": full}
        ).json()
        return data.get("students", [])

    def get_merged_classes(
        self, class_id: int, ignore_merge_order: bool = False
    ) -> list[int]:
        """Return the IDs of classes that were merged into a class."""
        data = self._session.get(
            f"/merged-classes/{class_id}",
            params={"ignore_merge_order": ignore_merge_order},
        ).json()
        return data.get("merged_class_ids", [])
