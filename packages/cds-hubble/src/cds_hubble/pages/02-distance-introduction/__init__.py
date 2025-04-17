
import solara
from solara.toestand import Ref

from ...components import Stage2Slideshow, STAGE_2_SLIDESHOW_LENGTH
from ...state import LOCAL_STATE, GLOBAL_STATE, get_multiple_choice, mc_callback
from .component_state import COMPONENT_STATE
from ...remote import LOCAL_API
from ...utils import get_image_path, DISTANCE_CONSTANT, push_to_route

from cds_core.logger import setup_logger

logger = setup_logger("STAGE 2")

@solara.component
def Page():
    solara.Title("HubbleDS")
    loaded_component_state = solara.use_reactive(False)
    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    def _load_component_state():
        # Load stored component state from database, measurement data is
        # considered higher-level and is loaded when the story starts
        LOCAL_API.get_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)

        # TODO: What else to we need to do here?
        logger.info("Finished loading component state for stage 2.")
        loaded_component_state.set(True)

    solara.use_memo(_load_component_state, dependencies=[])

    def _write_component_state():
        if not loaded_component_state.value:
            return

        # Listen for changes in the states and write them to the database
        res = LOCAL_API.put_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)
        
        if res:
            logger.info("Wrote component state for stage 2 to database.")
        else:
            logger.info("Did not write component state for stage 2 to database.")

    logger.info("Trying to write component state for stage 2.")
    solara.lab.use_task(_write_component_state, dependencies=[COMPONENT_STATE.value])

    step = Ref(
        COMPONENT_STATE.fields.distance_slideshow_state.step
    )
    max_step_completed = Ref(
        COMPONENT_STATE.fields.distance_slideshow_state.max_step_completed
    )

    speech = Ref(GLOBAL_STATE.fields.speech)
    Stage2Slideshow(
        step = COMPONENT_STATE.value.distance_slideshow_state.step,
        max_step_completed = COMPONENT_STATE.value.distance_slideshow_state.max_step_completed,
        length = STAGE_2_SLIDESHOW_LENGTH,
        titles = [
            "1920's Astronomy",
            "1920's Astronomy",
            "How can we know how far away something is?",
            "How can we know how far away something is?",
            "How can we know how far away something is?",
            "How can we know how far away something is?",
            "Galaxy Distances",
            "Galaxy Distances",
            "Galaxy Distances",
            "Galaxy Distances",
            "Galaxy Distances",
            "Galaxy Distances",
            "Galaxy Distances"
        ],
        interact_steps=[7,9],
        distance_const=DISTANCE_CONSTANT,
        image_location=get_image_path(router, "stage_two_intro"),
        event_set_step=step.set,
        event_set_max_step_completed=max_step_completed.set,
        event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
        state_view={
            "mc_score_1": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "which-galaxy-closer"),
            "score_tag_1": "which-galaxy-closer",
            "mc_score_2": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "how-much-closer-galaxies"), 
            "score_tag_2": "how-much-closer-galaxies",
        },
        event_return_to_stage1=lambda _: push_to_route(router, location, "01-spectra-&-velocity"),  
        event_slideshow_finished=lambda _: push_to_route(router, location, "03-distance-measurements"),
        debug = GLOBAL_STATE.value.show_team_interface,
        speech=speech.value.model_dump(),
    )
