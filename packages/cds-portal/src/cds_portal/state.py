"""Portal-level reactive state populated after login."""

from solara_state import BaseState, StateField, get_state as _get_state

from cds_client.models import Classroom, Educator, Student


class AuthState(BaseState):
    """Single source of truth for who is logged in, regardless of auth path."""
    authenticated: bool = StateField(default=False)
    auth_type: str | None = StateField(default=None)   # "oauth" | "student"
    user_ref: str | None = StateField(default=None)    # hashed_user (oauth) or username (student)
    display_name: str | None = StateField(default=None)
    picture: str | None = StateField(default=None)


class RegistrationPending(BaseState):
    """Persists role choice + educator form data across the Auth0 redirect."""
    role: str | None = StateField(default=None)         # "learner" | "educator"
    educator_data: dict | None = StateField(default=None)


class PortalState(BaseState):
    """DB-backed portal data loaded after authentication."""
    loading: bool = StateField(default=True)
    is_educator: bool = StateField(default=False)
    needs_setup: bool = StateField(default=False)
    setup_complete: int = StateField(default=0)

    student: Student | None = StateField(default=None)
    student_classes: list[Classroom] = StateField(default_factory=list)
    story_name: str = StateField(default="hubbles_law")
    total_stages: int = StateField(default=0)
    completed_stages: int = StateField(default=0)

    educator: Educator | None = StateField(default=None)
    educator_classes: list[Classroom] = StateField(default_factory=list)

    class_educator_names: dict[int, str] = StateField(default_factory=dict)
    class_progress: dict[int, float] = StateField(default_factory=dict)
    class_sizes: dict[int, int] = StateField(default_factory=dict)


def get_auth_state() -> AuthState:
    return _get_state(AuthState)


def get_registration_pending() -> RegistrationPending:
    return _get_state(RegistrationPending)


def get_portal_state() -> PortalState:
    return _get_state(PortalState)
