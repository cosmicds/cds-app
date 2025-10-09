import datetime
from typing import Callable, Tuple, Optional
from typing import TypeVar

from pydantic import BaseModel, computed_field
from pydantic import Field
from solara import Reactive
from solara.toestand import Ref

from cds_core.base_states import (
    BaseStoryState,
    MultipleChoiceResponse,
    FreeResponse,
    register_story,
)
from cds_core.logger import setup_logger
from .helpers.data_management import ELEMENT_REST

logger = setup_logger("HUBBLEDS-STATE")


class SpectrumData(BaseModel):
    name: str
    wave: list[float]
    flux: list[float]
    ivar: list[float]


class GalaxyData(BaseModel):
    id: int
    name: str
    ra: float
    decl: float
    z: float
    type: str
    element: str

    @property
    def rest_wave_value(self) -> float:
        return round(ELEMENT_REST[self.element])

    @property
    def redshift_rest_wave_value(self) -> float:
        return ELEMENT_REST[self.element] * (1 + self.z)


class StudentMeasurement(BaseModel):
    student_id: int
    class_id: int | None = None
    rest_wave_unit: str = "angstrom"
    obs_wave_value: float | None = None
    obs_wave_unit: str = "angstrom"
    velocity_value: float | None = None
    velocity_unit: str = "km / s"
    ang_size_value: float | None = None
    ang_size_unit: str = "arcsecond"
    est_dist_value: float | None = None
    est_dist_unit: str = "Mpc"
    measurement_number: str | None = None
    brightness: float = 0
    galaxy: Optional[GalaxyData] = None

    @computed_field
    @property
    def galaxy_id(self) -> int:
        return self.galaxy.id if self.galaxy else 0

    @computed_field
    @property
    def rest_wave_value(self) -> float:
        if self.galaxy:
            return self.galaxy.rest_wave_value
        return 0

    # @computed_field
    # @property
    # def last_modified(self) -> str:
    #     return f"{datetime.datetime.now(datetime.UTC)}"
    @property
    def completed(self) -> bool:
        return (
            self.obs_wave_value is not None
            and self.velocity_value is not None
            and self.ang_size_value is not None
            and self.est_dist_value is not None
        )


class BaseSummary(BaseModel):
    hubble_fit_value: Optional[float] = None
    hubble_fit_unit: str = "km / s"
    age_value: float
    age_unit: str = "Gyr"
    last_data_update: Optional[datetime.datetime] = None


class StudentSummary(BaseSummary):
    student_id: int


class ClassSummary(BaseSummary):
    class_id: int


@register_story("hubbles_law")
class StoryState(BaseStoryState):
    title: str = "Hubble's Law"
    story_id: str = "hubbles_law"
    type: str = "hubbles_law"
    measurements: list[StudentMeasurement] = []
    example_measurements: list[StudentMeasurement] = []
    class_measurements: list[StudentMeasurement] = []
    all_measurements: list[StudentMeasurement] = []
    student_summaries: list[StudentSummary] = []
    class_summaries: list[ClassSummary] = []
    measurements_loaded: bool = False
    calculations: dict = {}
    validation_failure_counts: dict = {}
    has_best_fit_galaxy: bool = False
    best_fit_slope: Optional[float] = None
    enough_students_ready: bool = False
    class_data_students: list = []
    class_data_info: dict = {}
    show_snackbar: bool = False
    snackbar_message: str = ""
    stage_4_class_data_students: list[int] = []
    stage_5_class_data_students: list[int] = []
    last_route: Optional[str] = None
    route_restored: bool = Field(False, exclude=True)
    # TODO: Remove these fields when the new state is fully implemented
    mc_scoring: dict[str, dict] = {"scores": {}}
    free_responses: dict[str, dict] = {"responses": {}}

    def as_dict(self):
        return self.model_dump(
            exclude={
                "example_measurements",
                "measurements",
                "measurements_loaded",
                "class_measurements",
                "all_measurements",
                "student_summaries",
                "class_summaries",
            }
        )

    def get_measurement(self, galaxy_id: int) -> StudentMeasurement | None:
        return next((x for x in self.measurements if x.galaxy_id == galaxy_id), None)

    def get_example_measurement(
        self, galaxy_id: int, measurement_number="first"
    ) -> StudentMeasurement | None:
        def check_example_galaxy(x: StudentMeasurement):
            return (
                x.galaxy_id == galaxy_id and x.measurement_number == measurement_number
            )

        return next(
            (x for x in self.example_measurements if check_example_galaxy(x)), None
        )

    def get_measurement_index(self, galaxy_id: int) -> int | None:
        return next(
            (i for i, x in enumerate(self.measurements) if x.galaxy_id == galaxy_id),
            None,
        )

    def get_example_measurement_index(
        self, galaxy_id: int, measurement_number="first"
    ) -> int | None:
        def check_example_galaxy(x: StudentMeasurement):
            return (
                x.galaxy_id == galaxy_id and x.measurement_number == measurement_number
            )

        return next(
            (
                i
                for i, x in enumerate(self.example_measurements)
                if check_example_galaxy(x)
            ),
            None,
        )


BaseComponentStateT = TypeVar("BaseComponentStateT", bound="BaseComponentState")


def mc_callback(
    event,
    local_state: Reactive[StoryState],
    component_state: Reactive[BaseComponentStateT],
    callback: Optional[Callable] = None,
):
    """
    Multiple Choice callback function
    """
    if event[0] == "mc-score":
        logger.debug(f"MC Score event received: {event[1]}")
        new_response = MultipleChoiceResponse(
            **{**event[1], "stage": component_state.value.stage_id}
        )
        Ref(component_state.fields.multiple_choice_responses[new_response.tag]).set(
            new_response
        )

        bank_total_ref = Ref(local_state.fields.piggybank_total)
        logger.debug(
            f"Updating piggy bank total from {bank_total_ref.value} to "
            f"{bank_total_ref.value + new_response.score}"
        )
        bank_total_ref.set(bank_total_ref.value + new_response.score)


def fr_callback(
    event: Tuple[str, dict[str, str]],
    local_state: Reactive[StoryState],
    component_state: Reactive[BaseComponentStateT],
    callback: Optional[Callable] = None,
):
    """
    Free Response callback function
    """
    if event[0] == "fr-update":
        logger.debug(f"Free Response update event received: {event[1]}")
        new_response = FreeResponse(
            **{**event[1], "stage": component_state.value.stage_id}
        )
        Ref(component_state.fields.free_responses[new_response.tag]).set(new_response)
