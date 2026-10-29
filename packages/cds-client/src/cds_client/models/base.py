"""Public models for the core CosmicDS API.

This module re-exports models from the auto-generated ``_generated_base``
module under stable, well-named identifiers.  Edit *this* file for renames or
additions; never edit ``_generated_base.py`` directly.
"""

from ._generated_base import (
    Class as Classroom,  # avoid importing a name that reads like a keyword
    ClassCreated,
    ClassCreationInfo,
    ClassStories,
    EducatorCreated,
    EducatorCreationInfo,
    Educator as _GeneratedEducator,
    Error,
    Question,
    QuestionCreationInfo,
    Stage,
    StageState,
    Status as ClassStatus,  # scoped name; Status alone is too ambiguous
    Status1 as CreationStatus,  # generated collision name -> descriptive
    StoryState,
    Student as _GeneratedStudent,
    StudentCreated,
    StudentCreationInfo,
    User,
)


# The generated models mark several fields as required strings, but the API
# can return null for them. Override only the affected fields; everything else
# is inherited from the generated class.

class Student(_GeneratedStudent):
    verification_code: str | None = None
    institution: str | None = None
    gender: str | None = None
    ip: str | None = None
    lat: str | None = None
    lon: str | None = None
    last_visit_ip: str | None = None
    team_member: str | None = None


class Educator(_GeneratedEducator):
    verification_code: str | None = None
    institution: str | None = None
    gender: str | None = None
    ip: str | None = None
    lat: str | None = None
    lon: str | None = None
    last_visit_ip: str | None = None


__all__ = [
    "Classroom",
    "ClassCreated",
    "ClassCreationInfo",
    "ClassStatus",
    "ClassStories",
    "CreationStatus",
    "Educator",
    "EducatorCreated",
    "EducatorCreationInfo",
    "Error",
    "Question",
    "QuestionCreationInfo",
    "Stage",
    "StageState",
    "StoryState",
    "Student",
    "StudentCreated",
    "StudentCreationInfo",
    "User",
]
