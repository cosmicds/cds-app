import solara
from cds_core.layout import BaseLayout, BaseSetup
from cds_core.logger import setup_logger
from .remote import LOCAL_API
from .utils import push_to_route
from solara.toestand import Ref

from .state import GLOBAL_STATE, LOCAL_STATE

logger = setup_logger("LAYOUT")


@solara.component
def Layout(children=[]):
    BaseSetup(
        story_name=LOCAL_STATE.value.story_id, story_title=LOCAL_STATE.value.title
    )

    student_id = Ref(GLOBAL_STATE.fields.student.id)
    loaded_states = solara.use_reactive(False)
    route_restored = Ref(LOCAL_STATE.fields.route_restored)

    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    route_current, routes_current_level = solara.use_route(peek=True)
    route_index = routes_current_level.index(route_current)

    def _load_global_local_states():
        # Force reset global and local states
        logger.info("Clearing local states.")
        LOCAL_STATE.set(LOCAL_STATE.value.__class__())

        if student_id.value is None:
            logger.warning(
                f"Failed to load measurements: ID `{GLOBAL_STATE.value.student.id}` not found."
            )
            return

        logger.info(
            "Loading story stage and measurements for user `%s`.",
            GLOBAL_STATE.value.student.id,
        )

        # Retrieve the student's app and local states
        LOCAL_API.get_app_story_states(GLOBAL_STATE, LOCAL_STATE)

        # Load in the student's measurements
        measurements = LOCAL_API.get_measurements(GLOBAL_STATE, LOCAL_STATE)
        sample_measurements = LOCAL_API.get_sample_measurements(
            GLOBAL_STATE, LOCAL_STATE
        )

        logger.info("Finished loading state.")

        Ref(LOCAL_STATE.fields.measurements_loaded).set(True)

        loaded_states.set(True)

    solara.use_memo(_load_global_local_states, dependencies=[])

    def _write_local_global_states():
        if not loaded_states.value:
            return

        # Listen for changes in the states and write them to the database
        put_state = LOCAL_API.put_story_state(GLOBAL_STATE, LOCAL_STATE)

        # Be sure to write the measurement data separately since it's stored
        #  in another location in the database
        put_meas = LOCAL_API.put_measurements(GLOBAL_STATE, LOCAL_STATE)
        put_samp = LOCAL_API.put_sample_measurements(GLOBAL_STATE, LOCAL_STATE)

        if put_state and put_meas and put_samp:
            logger.info("Wrote state to database.")
        else:
            logger.info(
                f"Did not write {'story state' if not put_state else ''} "
                f"{'measurements' if not put_meas else ''} "
                f"{'sample measurements' if not put_samp else ''} "
                f"to database."
            )

    solara.lab.use_task(
        _write_local_global_states, dependencies=[GLOBAL_STATE.value, LOCAL_STATE.value]
    )

    def _store_user_location():
        if not route_restored.value:
            return

        logger.info(f"Storing path location as `{route_current.path}`")
        # Store the current route index so that users will be returned to their
        #  previous location when they return to the app
        Ref(LOCAL_STATE.fields.last_route).set(f"{route_current.path}")
        Ref(LOCAL_STATE.fields.max_route_index).set(
            max(route_index or 0, LOCAL_STATE.value.max_route_index or 0)
        )

    solara.use_effect(_store_user_location, dependencies=[route_current])

    def _restore_user_location():
        if not route_restored.value:
            if (
                LOCAL_STATE.value.last_route is not None
                and route_current.path != LOCAL_STATE.value.last_route
            ):
                logger.info(
                    f"Restoring path location to `{LOCAL_STATE.value.last_route}`"
                )
                push_to_route(router, location, LOCAL_STATE.value.last_route)
            else:
                route_restored.set(True)

    solara.use_memo(_restore_user_location)

    # The rendering takes a moment while the route resolves, this can appear as
    #  a flicker before the true page loads. Here, we hide the page until the
    #  route is restored.
    if route_restored.value:
        BaseLayout(
            local_state=LOCAL_STATE,
            children=children,
            story_name=LOCAL_STATE.value.story_id,
            story_title=LOCAL_STATE.value.title,
        )
