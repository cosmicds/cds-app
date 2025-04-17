from pydantic import BaseModel, computed_field, field_validator, Field
from solara import Reactive
from cds_core.state import BaseState, GLOBAL_STATE, BaseLocalState
from .base_component_state import BaseComponentState
from typing import Optional
import solara
import datetime
from functools import cached_property
from astropy.table import Table
from pydantic import Field

from solara.toestand import Ref


from typing import Callable, Tuple

from .data_management import ELEMENT_REST

from cds_core.logger import setup_logger

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

    @cached_property
    def spectrum(self):
        from .remote import LOCAL_API

        return LOCAL_API.load_spectrum_data(self, LOCAL_STATE)

    @cached_property
    def spectrum_as_data_frame(self):
        from .remote import LOCAL_API

        spec_data = LOCAL_API.load_spectrum_data(self, LOCAL_STATE)

        return Table({"wave": spec_data.wave, "flux": spec_data.flux}).to_pandas()

    @property
    def rest_wave_value(self) -> float:
        return round(ELEMENT_REST[self.element])

    @property
    def redshift_rest_wave_value(self) -> float:
        return (ELEMENT_REST[self.element] * (1 + self.z))


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



class LocalState(BaseLocalState):
    title: str = "Hubble's Law"
    story_id: str = "hubbles_law"
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
    mc_scoring: dict[str, dict] = {'scores': {}}
    free_responses: dict[str, dict]= {'responses': {}}
    show_snackbar: bool = False
    snackbar_message: str = ""
    stage_4_class_data_students: list[int] = []
    stage_5_class_data_students: list[int] = []
    last_route: Optional[str] = None
    route_restored: bool = Field(False, exclude=True)

    @cached_property
    def galaxies(self) -> dict[int, GalaxyData]:
        from .remote import LOCAL_API

        gal_data = LOCAL_API.get_galaxies(LOCAL_STATE)
        return { galaxy.id: galaxy for galaxy in gal_data }

    def as_dict(self):
        return self.model_dump(exclude={
            "example_measurements",
            "measurements",
            "measurements_loaded",
            "class_measurements",
            "all_measurements",
            "student_summaries",
            "class_summaries",
        })

    def get_measurement(self, galaxy_id: int) -> StudentMeasurement | None:
        return next((x for x in self.measurements if x.galaxy_id == galaxy_id), None)

    def get_example_measurement(self, galaxy_id: int, measurement_number = 'first') -> StudentMeasurement | None:
        def check_example_galaxy(x: StudentMeasurement):
            return x.galaxy_id == galaxy_id and x.measurement_number == measurement_number
        
        return next(
            (x for x in self.example_measurements if check_example_galaxy(x)), None
        )

    def get_measurement_index(self, galaxy_id: int) -> int | None:
        return next(
            (i for i, x in enumerate(self.measurements) if x.galaxy_id == galaxy_id),
            None,
        )

    def get_example_measurement_index(self, galaxy_id: int, measurement_number = 'first') -> int | None:
        def check_example_galaxy(x: StudentMeasurement):
            return x.galaxy_id == galaxy_id and x.measurement_number == measurement_number
        
        return next(
            (
                i
                for i, x in enumerate(self.example_measurements)
                if check_example_galaxy(x)
            ),
            None,
        )

    def question_completed(self, tag: str) -> bool:
        if tag in self.free_responses['responses']:
            return self.free_responses['responses'][tag]['response'] != ""
        elif tag in self.mc_scoring['scores']:
            return self.mc_scoring['scores'][tag]['score'] is not None

        return False


LOCAL_STATE = solara.reactive(LocalState())

from typing import TypeVar
BaseComponentStateT = TypeVar('BaseComponentStateT', bound='BaseComponentState')

def get_free_response(local_state: Reactive[LocalState], component_state: Reactive[BaseComponentStateT], tag: str):
    logger.debug(f"Getting Free Response for tag: {tag}")
    # check if the question present
    if tag in local_state.value.free_responses['responses']:
        
        return local_state.value.free_responses['responses'][tag]
    
    # Create question on Ref
    free_responses = Ref(local_state.fields.free_responses).value.copy()['responses']
    new = dict(tag=tag, response="", initialized=True, stage=component_state.value.stage_id)
    free_responses = {**free_responses, tag: new }
    Ref(local_state.fields.free_responses).set({'responses': free_responses})
    return free_responses[tag]


def fix_free_responses_stage_missing(tag, local_state: Reactive[LocalState], component_state: Reactive[BaseComponentStateT]):
    # just add the state if it's missing
    free_responses = Ref(local_state.fields.free_responses).value.copy()['responses']
    if tag not in free_responses.keys():
        new = dict(tag=tag, response="", initialized=True, stage=component_state.value.stage_id)
        free_responses = {**free_responses, tag: new }
        Ref(local_state.fields.free_responses).set({'responses': free_responses})
        
        
def get_multiple_choice(local_state: Reactive[LocalState], component_state: Reactive[BaseComponentStateT], tag: str):
    logger.debug(f"Getting MC Score for tag: {tag}")
    if tag in local_state.value.mc_scoring['scores']:
        if 'stage' not in local_state.value.mc_scoring['scores'][tag]:
            new = local_state.value.mc_scoring['scores'][tag]
            new['stage'] = component_state.value.stage_id
            mc_scoring = {**local_state.value.mc_scoring['scores'], tag: new }
        return local_state.value.mc_scoring['scores'][tag]
    
    mc_scoring = Ref(local_state.fields.mc_scoring).value.copy()['scores']
    new = dict(tag=tag, score=None, choice=None, tries=0, wrong_attempts=0, stage=component_state.value.stage_id)
    mc_scoring = {**mc_scoring, tag: new }
    Ref(local_state.fields.mc_scoring).set({'scores': mc_scoring})
    return mc_scoring[tag]


def mc_callback(
    event,
    local_state: Reactive[LocalState],
    component_state: Reactive[BaseComponentStateT],
    callback: Optional[Callable] = None,
):
    """
    Multiple Choice callback function
    """

    mc_scoring = Ref(local_state.fields.mc_scoring).value.copy()['scores']
    piggybank_total = Ref(local_state.fields.piggybank_total)

    # mc-initialize-callback returns data which is a string
    if event[0] == "mc-initialize-response":
        # check for a missing tag
        if event[1] not in mc_scoring.keys():
            logger.debug(f"Initializing MC Score for tag: {event[1]}")
            new_score = dict(
                tag=event[1], 
                score=None, 
                choice=None, 
                tries=0, 
                wrong_attempts=0,
                stage=component_state.value.stage_id
                )
            mc_scoring = {**mc_scoring, event[1]: new_score}
            Ref(local_state.fields.mc_scoring).set({'scores': mc_scoring})

    # mc-score event returns a data which is an mc-score dictionary (includes tag)
    elif event[0] == "mc-score":
        new_score = mc_scoring[event[1]["tag"]].copy() # make a copy of the current score
        if 'stage' not in new_score:
            new_score['stage'] = component_state.value.stage_id
        new_score.update(event[1]) # update with new score, choice, tries, and wrong_attempts, but keeps the stage
        mc_scoring = {**mc_scoring, event[1]["tag"]: new_score} # update the score
        Ref(local_state.fields.mc_scoring).set({'scores': mc_scoring})

        # update piggybank_total
        try:
            # try except is a hold over from old code, but haven't checked for weird edge cases
            if event[1]["score"] is not None:
                score = int(event[1]["score"])
            else:
                score = 0
        except (TypeError, ValueError):
            logger.error(f"Invalid score value for tag:{event[1]['tag']}: {event[1]['score']}")
            score = 0
        total_score = piggybank_total.value + score
        piggybank_total.set(total_score)

        if callback is not None:
            callback()

    else:
        raise ValueError(f"Unknown event in mc_callback: <<{event}>> ")




def fr_callback(
    event: Tuple[str, dict[str, str]],
    local_state: Reactive[LocalState],
    component_state: Reactive[BaseComponentStateT],
    callback: Optional[Callable] = None,
):
    """
    Free Response callback function
    """
    
    free_responses = Ref(local_state.fields.free_responses).value.copy()['responses']
    
    if event[0] == "fr-initialize":
        if event[1]["tag"] not in free_responses.keys():
            logger.debug(f"Initializing Free Response for tag: {event[1]['tag']}")
            new = dict(tag=event[1]["tag"], response="", initialized=True, stage=component_state.value.stage_id)
            free_responses = {**free_responses, event[1]["tag"]: new }
            Ref(local_state.fields.free_responses).set({'responses': free_responses})
            if callback is not None:
                callback()
    elif event[0] == "fr-update":
        new = free_responses[event[1]["tag"]]
        new['response'] = event[1]["response"]
        free_responses = {**free_responses, event[1]["tag"]: new }
        if 'stage' not in free_responses[event[1]["tag"]]:
            new = free_responses[event[1]["tag"]]
            new['stage'] = component_state.value.stage_id
            free_responses = {**free_responses, event[1]["tag"]: new }
        Ref(local_state.fields.free_responses).set({'responses': free_responses})
        if callback is not None:
                callback()
    else:
        raise ValueError(f"Unknown event in fr_callback: <<{event}>> ")
