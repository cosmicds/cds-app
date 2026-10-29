from .auth import get_hashed_user, hash_user
from .client import CDSClient, HubbleClient
from .exceptions import CDSAPIError, CDSAuthError, CDSConflictError, CDSNotFoundError
from .models import (
    Classroom,
    ClassCreationInfo,
    ClassStatus,
    ClassStories,
    CreationStatus,
    Educator,
    EducatorCreationInfo,
    Element,
    Galaxy,
    HubbleAllData,
    HubbleClassData,
    HubbleMeasurement,
    HubbleMeasurementInput,
    HubbleSampleMeasurement,
    HubbleSampleMeasurementInput,
    HubbleStudentData,
    MinimalGalaxy,
    MinimalHubbleMeasurement,
    MinimalHubbleStudentData,
    Question,
    SpectrumData,
    Stage,
    StageState,
    StoryState,
    Student,
    StudentCreationInfo,
)
from .session import CDSSession
from .state import ClassroomState, EducatorState, StudentState, get_state

__all__ = [
    # client
    "CDSClient",
    "HubbleClient",
    "CDSSession",
    # auth
    "hash_user",
    "get_hashed_user",
    # exceptions
    "CDSAPIError",
    "CDSAuthError",
    "CDSConflictError",
    "CDSNotFoundError",
    # models – base
    "Classroom",
    "ClassCreationInfo",
    "ClassStatus",
    "ClassStories",
    "CreationStatus",
    "Educator",
    "EducatorCreationInfo",
    "Question",
    "Stage",
    "StageState",
    "StoryState",
    "Student",
    "StudentCreationInfo",
    # models – hubble
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
    # state
    "ClassroomState",
    "EducatorState",
    "StudentState",
    "get_state",
]
