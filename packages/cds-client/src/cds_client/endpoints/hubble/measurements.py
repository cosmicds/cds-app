from datetime import date
from typing import Any

from ...exceptions import CDSNotFoundError
from ...models.hubble import (
    HubbleAllData,
    HubbleClassData,
    HubbleMeasurement,
    HubbleMeasurementInput,
    HubbleSampleMeasurement,
    HubbleSampleMeasurementInput,
    HubbleStudentData,
)
from ..base import BaseEndpoint


class MeasurementsEndpoint(BaseEndpoint):
    """Hubble's Law measurement endpoints."""

    # Student measurements
    def get(self, student_id: int) -> list[HubbleMeasurement]:
        """Return all measurements for a student."""
        data = self._session.get(f"/measurements/{student_id}").json()
        return [HubbleMeasurement(**m) for m in data.get("measurements", [])]

    def get_one(self, student_id: int, galaxy_id: int) -> HubbleMeasurement | None:
        """Return a specific galaxy measurement for a student."""
        try:
            data = self._session.get(
                f"/measurements/{student_id}/{galaxy_id}"
            ).json()
        except CDSNotFoundError:
            return None
        m = data.get("measurement")
        return HubbleMeasurement(**m) if m else None

    def submit(self, measurement: HubbleMeasurementInput) -> HubbleMeasurement:
        """Submit (upsert) a student measurement."""
        data = self._session.put(
            "/submit-measurement", json=measurement.model_dump(exclude_none=True)
        ).json()
        return HubbleMeasurement(**data)

    def delete(self, student_id: int, galaxy_identifier: str | int) -> None:
        """Delete a student's measurement for a galaxy."""
        self._session.delete(f"/measurement/{student_id}/{galaxy_identifier}")

    # Sample measurements
    def get_sample(self, student_id: int) -> list[HubbleSampleMeasurement]:
        """Return sample (example) measurements for a student."""
        data = self._session.get(f"/sample-measurements/{student_id}").json()
        return [HubbleSampleMeasurement(**m) for m in data.get("measurements", [])]

    def get_sample_one(
        self, student_id: int, measurement_number: str
    ) -> HubbleSampleMeasurement | None:
        """Return one sample measurement (``"first"`` or ``"second"``)."""
        try:
            data = self._session.get(
                f"/sample-measurements/{student_id}/{measurement_number}"
            ).json()
        except CDSNotFoundError:
            return None
        m = data.get("measurement")
        return HubbleSampleMeasurement(**m) if m else None

    def submit_sample(
        self, measurement: HubbleSampleMeasurementInput
    ) -> HubbleSampleMeasurement:
        """Submit (upsert) a sample measurement."""
        data = self._session.put(
            "/sample-measurement", json=measurement.model_dump(exclude_none=True)
        ).json()
        return HubbleSampleMeasurement(**data)

    def delete_sample(self, student_id: int, measurement_number: str) -> None:
        """Delete a sample measurement (``"first"`` or ``"second"``)."""
        self._session.delete(f"/sample-measurement/{student_id}/{measurement_number}")

    def list_all_sample(
        self, measurement_number: str | None = None
    ) -> list[HubbleSampleMeasurement]:
        """Return all sample measurements, optionally filtered by number."""
        path = (
            f"/sample-measurements/{measurement_number}"
            if measurement_number
            else "/sample-measurements"
        )
        data = self._session.get(path).json()
        items = data if isinstance(data, list) else data.get("measurements", [])
        return [HubbleSampleMeasurement(**m) for m in items]

    # Class measurements
    def get_class(
        self,
        student_id: int,
        class_id: int,
        complete_only: bool = False,
        exclude_student: bool = False,
        student_ids: list[int] | None = None,
    ) -> list[HubbleMeasurement]:
        """Return all measurements for a class."""
        params: dict[str, Any] = {"complete_only": complete_only}
        if exclude_student:
            params["exclude_student"] = True
        if student_ids:
            params["student_ids"] = student_ids
        data = self._session.get(
            f"/class-measurements/{student_id}/{class_id}", params=params
        ).json()
        return [HubbleMeasurement(**m) for m in data.get("measurements", [])]

    def get_class_size(
        self, student_id: int, class_id: int, complete_only: bool = False
    ) -> int:
        """Return the number of measurements in a class."""
        data = self._session.get(
            f"/class-measurements/size/{student_id}/{class_id}",
            params={"complete_only": complete_only},
        ).json()
        return data["measurement_count"]

    def get_students_completed_count(self, student_id: int, class_id: int) -> int:
        """Return how many students have completed all measurements in a class."""
        data = self._session.get(
            f"/class-measurements/students-completed/{student_id}/{class_id}"
        ).json()
        return data["students_completed_measurements"]

    # Aggregate data
    def get_all_data(
        self,
        class_id: int | None = None,
        minimal: bool = False,
        before: date | None = None,
    ) -> HubbleAllData:
        """Return all measurements and summary data."""
        params: dict[str, Any] = {"minimal": minimal}
        if class_id is not None:
            params["class_id"] = class_id
        if before is not None:
            params["before"] = before.isoformat()
        data = self._session.get("/all-data", params=params).json()
        return HubbleAllData(
            measurements=[
                HubbleMeasurement(**m)
                for m in data.get("measurements", [])
                if m.get("class_id") is not None
            ],
            student_data=[
                HubbleStudentData(**s) for s in data.get("studentData", [])
            ],
            class_data=[
                HubbleClassData(**c) for c in data.get("classData", [])
            ],
        )
