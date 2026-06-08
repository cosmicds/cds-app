"""Reactive state containers for the CosmicDS client.

Each class is a ``solara_state.BaseState`` subclass, meaning every field is
backed by a ``solara.Reactive`` ref via the descriptor protocol.  Use the
module-level ``get_state()`` helper to access the per-session singletons, or
instantiate them locally for component-scoped state.

Example::

    from cds_client.state import get_state, StudentState, ClassroomState

    # Global singleton – shared across components in the same session
    student = get_state(StudentState)
    student.student_id.value  # reactive read
    student.student_id.value = 42  # reactive write (triggers subscriptions)

    # Or wrap in solara.reactive for use in component trees
    import solara
    reactive_student = solara.reactive(StudentState())
"""

from solara_state import BaseState, StateField, get_state as _get_state

from .models.base import Classroom, Educator, Student


class StudentState(BaseState):
    """Reactive state for the currently authenticated student."""

    student_id: int = StateField(default=0)
    username: str = StateField(default="")
    hashed_user: str | None = StateField(default=None)
    data: Student | None = StateField(default=None)
    is_educator: bool = StateField(default=False)
    update_db: bool = StateField(default=True)


class ClassroomState(BaseState):
    """Reactive state for the student's current classroom."""

    class_info: dict = StateField(default_factory=dict)
    size: int = StateField(default=0)
    data: Classroom | None = StateField(default=None)


class EducatorState(BaseState):
    """Reactive state for the currently authenticated educator."""

    educator_id: int = StateField(default=0)
    username: str = StateField(default="")
    hashed_user: str | None = StateField(default=None)
    data: Educator | None = StateField(default=None)


def get_state(state_class):
    """Return the global singleton for *state_class* (thread-safe).

    This is a thin wrapper around ``solara_state.get_state`` re-exported here
    for convenience so callers only need to import from ``cds_client``.
    """
    return _get_state(state_class)
