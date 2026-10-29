import json
from typing import Any

from ..exceptions import CDSNotFoundError
from ..models.base import Question, Stage, StageState, StoryState
from .base import BaseEndpoint


class StoriesEndpoint(BaseEndpoint):
    """Endpoints for story and stage state management."""

    # Story state
    def get_story_state(self, student_id: int, story_name: str) -> StoryState | None:
        """Fetch a student's story state."""
        try:
            data = self._session.get(
                f"/story-state/{student_id}/{story_name}"
            ).json()
        except CDSNotFoundError:
            return None
        return StoryState(**data) if data else None

    def put_story_state(
        self, student_id: int, story_name: str, state: dict[str, Any]
    ) -> StoryState:
        """Replace a student's story state."""
        data = self._session.put(
            f"/story-state/{student_id}/{story_name}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(state),
        ).json()
        return StoryState(**data)

    def patch_story_state(
        self, student_id: int, story_name: str, patch: dict[str, Any]
    ) -> StoryState:
        """Partially update a student's story state."""
        data = self._session.patch(
            f"/story-state/{student_id}/{story_name}",
            headers={"Content-Type": "application/json"},
            data=json.dumps(patch),
        ).json()
        return StoryState(**data)

    # Stage state
    def get_stages(self, story_name: str) -> list[Stage]:
        """Return the ordered list of stages for a story."""
        data = self._session.get(f"/stages/{story_name}").json()
        items = data.get("stages", data) if isinstance(data, dict) else data
        return [
            Stage(**s) if isinstance(s, dict)
            else Stage(story_name=story_name, stage_name=s)
            for s in items
        ]

    def get_stage_state(
        self, student_id: int, story_name: str, stage_name: str
    ) -> StageState | None:
        """Fetch a student's state for one stage."""
        try:
            data = self._session.get(
                f"/stage-state/{student_id}/{story_name}/{stage_name}"
            ).json()
        except CDSNotFoundError:
            return None
        return StageState(**data) if data else None

    def list_stage_states(
        self,
        story_name: str,
        student_id: int | None = None,
        class_id: int | None = None,
        stage_name: str | None = None,
    ) -> list[StageState]:
        """Fetch stage states with optional filtering."""
        params: dict[str, Any] = {}
        if student_id is not None:
            params["student_id"] = student_id
        if class_id is not None:
            params["class_id"] = class_id
        if stage_name is not None:
            params["stage_name"] = stage_name
        data = self._session.get(f"/stage-states/{story_name}", params=params).json()
        items = list(data) if isinstance(data, list) else [
            entry for entries in data.values() for entry in entries
        ]
        return [StageState(**s) for s in items]

    def count_completed_stages(self, story_name: str, student_id: int) -> int:
        """Return the number of stages a student has completed for a story."""
        params = {"student_id": student_id}
        data = self._session.get(f"/stage-states/{story_name}", params=params).json()
        return len(data) if isinstance(data, dict) else len(data)

    def count_class_stage_states(self, story_name: str, class_id: int) -> int:
        """Return the total number of completed stage states across all students in a class.

        Counts raw entries without model instantiation so it is robust to the
        nested response shape the class-scoped endpoint returns.
        """
        data = self._session.get(
            f"/stage-states/{story_name}", params={"class_id": class_id}
        ).json()
        if isinstance(data, list):
            return len(data)
        if isinstance(data, dict):
            return sum(len(v) if isinstance(v, (list, dict)) else 1 for v in data.values())
        return 0

    def put_stage_state(
        self,
        student_id: int,
        story_name: str,
        stage_name: str,
        state: dict[str, Any],
    ) -> StageState:
        """Replace a student's state for one stage."""
        data = self._session.put(
            f"/stage-state/{student_id}/{story_name}/{stage_name}",
            json=state,
        ).json()
        return StageState(**data)

    def delete_stage_state(
        self, student_id: int, story_name: str, stage_name: str
    ) -> None:
        """Delete a student's state for one stage."""
        self._session.delete(
            f"/stage-state/{student_id}/{story_name}/{stage_name}"
        )

    # Questions
    def get_question(self, tag: str) -> Question | None:
        """Fetch a question by its tag."""
        try:
            data = self._session.get(f"/question/{tag}").json()
        except CDSNotFoundError:
            return None
        return Question(**data) if data else None

    def get_questions(self, story_name: str) -> list[Question]:
        """Return all questions for a story."""
        data = self._session.get(f"/questions/{story_name}").json()
        return [Question(**q) for q in data]
