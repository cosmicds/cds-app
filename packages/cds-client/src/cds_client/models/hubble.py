"""Public models for the Hubble's Law story API.

This module re-exports models from the auto-generated ``_generated_hubble``
module and defines composite models that are not present in the API schema.
Edit *this* file for renames or additions; never edit ``_generated_hubble.py``
directly.
"""

from pydantic import BaseModel

from ._generated_hubble import (
    Element,
    Galaxy,
    HubbleClassData,
    HubbleMeasurement,
    HubbleMeasurementInput,
    HubbleSampleMeasurement,
    HubbleSampleMeasurementInput,
    HubbleStudentData,
    MinimalGalaxy,
    MinimalHubbleMeasurement,
    MinimalHubbleStudentData,
)


# Composite models not present in the API schema


class HubbleAllData(BaseModel):
    """Aggregated class data returned by the all-data endpoint."""

    measurements: list[HubbleMeasurement] = []
    student_data: list[HubbleStudentData] = []
    class_data: list[HubbleClassData] = []


class SpectrumData(BaseModel):
    """Spectrum arrays returned by the galaxy spectrum endpoint."""

    name: str
    wave: list[float]
    flux: list[float]
    ivar: list[float]


__all__ = [
    "Element",
    "Galaxy",
    "HubbleAllData",
    "HubbleClassData",
    "HubbleMeasurement",
    "HubbleMeasurementInput",
    "HubbleSampleMeasurement",
    "HubbleSampleMeasurementInput",
    "HubbleStudentData",
    "MinimalGalaxy",
    "MinimalHubbleMeasurement",
    "MinimalHubbleStudentData",
    "SpectrumData",
]
