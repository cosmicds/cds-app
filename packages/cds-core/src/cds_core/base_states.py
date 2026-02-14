import enum
from inspect import isclass
import os
from types import UnionType
from typing import (
    Dict,
    TypeVar,
    ClassVar,
    Type,
    Optional,
    Annotated,
    Union,
    Literal,
    Callable,
    Any,
    get_origin,
)

from pydantic import (
    BaseModel,
    Field,
    SerializationInfo,
    SerializerFunctionWrapHandler,
    ValidationInfo,
    computed_field,
    field_serializer,
    field_validator,
)
from solara import Reactive
from solara.toestand import Ref

from cds_core.logger import setup_logger

logger = setup_logger("STATE")

debug_mode_init = os.getenv("CDS_DEBUG_MODE", "false").strip().lower() == "true"

logger.info(f"Debug mode is {'enabled' if debug_mode_init else 'disabled'}. ")


# Create separate registries
STAGE_REGISTRY: Dict[str, Type["BaseStageState"]] = {}
STORY_REGISTRY: Dict[str, Type["BaseStoryState"]] = {}


def register_stage(state_name: str):

    def decorator(cls: Type["BaseStageState"]) -> Type["BaseStageState"]:
        setattr(cls, "type", state_name)

        STAGE_REGISTRY[state_name] = cls
        return cls

    return decorator


def register_story(state_name: str):

    def decorator(cls: Type["BaseStoryState"]) -> Type["BaseStoryState"]:
        setattr(cls, "type", state_name)

        STORY_REGISTRY[state_name] = cls
        return cls

    return decorator


class BaseMarker(enum.Enum):

    def __lt__(self, other):
        if type(other) is type(self):
            return self.value < other.value
        return NotImplemented

    def __gt__(self, other):
        if type(other) is type(self):
            return self.value > other.value
        return NotImplemented

    # We don't want to just do e.g. `not self.__lt__(other)` because __lt__ might return NotImplemented.
    # NotImplemented is truthy so `not NotImplemented` is False (with a `DeprecationWarning`)
    # but I think we want to actually return NotImplemented (for consistency with above)
    # and not a coerced boolean
    def __ge__(self, other):
        if type(other) is type(self):
            return self.value >= other.value
        return NotImplemented

    def __le__(self, other):
        if type(other) is type(self):
            return self.value <= other.value
        return NotImplemented

    @classmethod
    def next(cls, step):
        return cls(step.value + 1)

    @classmethod
    def previous(cls, step):
        return cls(step.value - 1)

    @classmethod
    def first(cls):
        return cls(1)

    @classmethod
    def last(cls):
        return cls(len(cls))

    def is_between(self, start: "BaseMarker", end: "BaseMarker"):
        return start.value <= self.value <= end.value

    @classmethod
    # Check if the given marker is at the specified marker or earlier.
    def is_at_or_before(cls, marker: "BaseMarker", end: "BaseMarker"):
        return marker.value <= end.value


class BaseState(BaseModel):

    @field_serializer("*", mode="wrap")
    def serialize_enums(
        self, value: Any, nxt: SerializerFunctionWrapHandler, _info: SerializationInfo
    ):
        if isinstance(value, BaseMarker):
            return value.value
        return nxt(value)

    @field_validator("*", mode="before")
    @classmethod
    def validate_marker(
        cls,
        value: Any,
        info: ValidationInfo,
    ) -> BaseMarker:
        # TODO: Can this be simplified?
        if info.field_name:
            annotation = cls.model_fields[info.field_name].annotation
            if annotation:
                origin = get_origin(annotation)
                if (
                    origin not in (Union, UnionType)
                    and isclass(origin)
                    and issubclass(origin, BaseMarker)
                ):
                    return annotation(value)
        return value

    def as_dict(self):
        return self.model_dump()

    def update(self, new):
        return self.model_copy(update=new)


BaseStageStateT = TypeVar("BaseStageStateT", bound="BaseStageState")


def transition_to(
    component_state: Reactive[BaseStageStateT], step: BaseMarker, force=False
):
    if component_state.value.can_transition(step) or force:
        Ref(component_state.fields.current_step).set(step)
    else:
        logger.warning(
            f"Conditions not met to transition from "
            f"{component_state.value.current_step.name} to {step.name}."
        )


def transition_next(component_state: Reactive[BaseStageStateT], force=False):
    next_marker = component_state.value.current_step.next(
        component_state.value.current_step
    )
    transition_to(component_state, next_marker, force=force)


def transition_previous(component_state: Reactive[BaseStageStateT], force=True):
    previous_marker = component_state.value.current_step.previous(
        component_state.value.current_step
    )
    transition_to(component_state, previous_marker, force=force)


class FreeResponse(BaseModel):
    tag: str
    response: str = ""
    initialized: bool = False
    stage: str = ""


class MultipleChoiceResponse(BaseModel):
    tag: str
    score: int = 0
    choice: int | None = None
    tries: int = 0
    wrong_attempts: int = 0
    stage: str = ""

    @field_validator("score", mode="before")
    @classmethod
    def coerce_none_to_zero(cls, v: Any):
        return 0 if v is None else int(v)


class BaseStageState(BaseState):
    type: str | None = None
    current_step: BaseMarker
    stage_id: str
    free_responses: Dict[str, FreeResponse] = Field(default_factory=dict)
    multiple_choice_responses: Dict[str, MultipleChoiceResponse] = Field(
        default_factory=dict
    )
    _max_step: int = 0  # not included in model

    def has_response(self, tag: str) -> bool:
        """Check if a response exists for the given tag."""
        if response := self.free_responses.get(tag):
            return response.response != ""
        elif response := self.multiple_choice_responses.get(tag):
            return response.score > 0

        return False

    # computed fields are included in the model when serialized
    @computed_field
    @property
    def max_step(self) -> int:
        self._max_step = max(self.current_step.value, self._max_step)  # type: ignore
        return self._max_step

    @computed_field
    @property
    def total_steps(self) -> int:
        # compute the total number of steps based on current_steps
        # this may be overridden in subclasses
        return len(self.current_step.__class__)

    @computed_field
    @property
    def progress(self) -> float:
        # TODO: this is inaccurate as it will always show that some progress
        #  has been made even if the user is on the first step. Likewise,
        #  stages with total steps of 1 will always show full progress.
        return self.max_step / self.total_steps

    def is_current_step(self, step: BaseMarker):
        return self.current_step.value == step.value

    def current_step_in(self, steps: list[BaseMarker]):
        return self.current_step in steps

    def can_transition(
        self,
        step: BaseMarker = None,
        next: bool = False,
        prev: bool = False,
    ):
        if next:
            if self.current_step is self.current_step.last():
                return False  # TODO: Fix once we sort out transitions between stages
            step = self.current_step.next(self.current_step)
        elif prev:
            if self.current_step is self.current_step.first():
                return False  # TODO: Fix once we sort out transitions between stages
            step = self.current_step.previous(self.current_step)

        return getattr(self, f"{step.name}_gate", True)

    def current_step_between(self, start: BaseMarker, end: BaseMarker = None):
        end = end or self.current_step.last()
        return self.current_step.is_between(start, end)

    def current_step_at_or_before(self, end):
        return self.current_step <= end

    def current_step_at_or_after(self, start):
        return self.current_step >= start


class BaseStoryState(BaseState):
    type: str | None = None
    debug_mode: bool = Field(debug_mode_init, exclude=True)
    title: str
    story_id: str
    piggybank_total: int = 0
    max_route_index: int | None = None
    stage_states: Dict[str, Annotated[object, ...]] = Field(default_factory=dict)

    def __init__(self, **data):
        self.patch_union_type()
        super().__init__(**data)
        for stage_name, stage_cls in STAGE_REGISTRY.items():
            if stage_name not in self.stage_states:
                self.stage_states[stage_name] = stage_cls()
                self.stage_states[stage_name].type = stage_cls.type

    @classmethod
    def patch_union_type(cls):
        StageStateUnionFactory = lambda: Annotated[
            Union[tuple(STAGE_REGISTRY.values())], Field(discriminator="type")
        ]
        cls.__annotations__["stage_states"] = dict[str, StageStateUnionFactory()]
        cls.model_rebuild()

    @field_validator("stage_states", mode="before")
    @classmethod
    def hydrate_stage_states(cls, v: Any) -> Dict[str, Annotated[object, ...]]:
        if isinstance(v, dict):
            res = {}

            for stage_name, stage_dict in v.items():
                if stage_name in STAGE_REGISTRY:
                    stage_cls = STAGE_REGISTRY[stage_name]
                    res[stage_name] = stage_cls(**stage_dict)
                    res[stage_name].type = stage_cls.type
                else:
                    logger.warning(f"Stage {stage_name} not found in registry.")

            return res
        return v


class BaseAppState(BaseState):
    story_state: Optional[Annotated[object, ...]] = None

    def __init__(self, **data):
        self.patch_union_type()
        super().__init__(**data)
        for story_name, story_cls in STORY_REGISTRY.items():
            self.story_state = story_cls()
            self.story_state.type = story_cls.type

    @classmethod
    def patch_union_type(cls):
        StoryStateUnionFactory = lambda: Annotated[
            Union[tuple(STORY_REGISTRY.values())], Field(discriminator="type")
        ]
        cls.__annotations__["story_states"] = StoryStateUnionFactory()
        cls.model_rebuild()

    @field_validator("story_state", mode="before")
    @classmethod
    def hydrate_story_states(cls, v: Any) -> Annotated[object, ...]:
        if isinstance(v, dict):
            if "type" in v:
                story_type = v["type"]
                if story_type in STORY_REGISTRY:
                    story_cls = STORY_REGISTRY[story_type]
                    return story_cls(**v)
                else:
                    logger.warning(f"Story type {story_type} not found in registry.")
            else:
                logger.warning("No 'type' field found in story state data.")
        return v
