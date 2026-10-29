import time

import solara
import os
from solara import Reactive
from solara.lab import Ref
from solara.lab import cookies as solara_cookies
from solara_enterprise import auth

from cds_client.cookies import verify_student_cookie
from cds_core.app_state import AppState
from cds_core.layout import BaseLayout, BaseSetup
from cds_core.logger import setup_logger
from .remote import LOCAL_API
from .story_state import StoryState
from .utils import push_to_route, extract_changed_subtree

logger = setup_logger("LAYOUT")

FORCE_DEMO = os.getenv("CDS_FORCE_DEMO", "false").strip().lower() == "true"


def _load_state(
    app_state: Reactive[AppState], story_state: Reactive[StoryState], *args, **kwargs
):
    # Force reset global and local states
    logger.info("Clearing local states.")
    story_state.set(story_state.value.__class__())

    logger.info(f"Student ID: {app_state.value.student.id}")
    logger.info(f"Class info: {app_state.value.classroom.class_info}")

    student_id = Ref(app_state.fields.student.id)

    if student_id.value is None:
        logger.warning(
            f"Failed to load measurements: ID `{app_state.value.student.id}` not found."
        )
        return

    logger.info(
        "Loading story stage and measurements for user `%s`.",
        app_state.value.student.id,
    )

    # Retrieve the student's app and local states
    LOCAL_API.get_app_story_states(app_state, story_state)

    # Load in the student's measurements
    measurements = LOCAL_API.get_measurements(app_state, story_state)
    sample_measurements = LOCAL_API.get_sample_measurements(app_state, story_state)

    logger.info("Finished loading state.")

    Ref(story_state.fields.measurements_loaded).set(True)


def _write_state(
    patch: dict, app_state: Reactive[AppState], story_state: Reactive[StoryState]
):
    # Listen for changes in the states and write them to the database
    patch_state = LOCAL_API.patch_story_state(patch, app_state, story_state)

    # Be sure to write the measurement data separately since it's stored
    #  in another location in the database
    put_meas = LOCAL_API.put_measurements(app_state, story_state)
    put_samp = LOCAL_API.put_sample_measurements(app_state, story_state)

    if patch_state and put_meas and put_samp:
        logger.info("Wrote state to database.")
    else:
        logger.info(
            f"Did not write {'story state' if not patch_state else ''} "
            f"{'measurements' if not put_meas else ''} "
            f"{'sample measurements' if not put_samp else ''} "
            f"to database."
        )


def Layout(
    children=[],
    app_state: Reactive[AppState] = None,
    story_state: Reactive[StoryState] = None,
):
    all_cookies = solara_cookies.use_value()

    def _ensure_student_auth():
        """Inject a synthetic auth.user from the student session cookie.

        Must run before BaseSetup so that _initial_setup sees an authenticated user.
        """
        if auth.user.value is not None:
            return
        cookie_val = all_cookies.get("cds_student", "")
        if not cookie_val:
            return
        username = verify_student_cookie(cookie_val)
        if username is None:
            return
        auth.user.set({"userinfo": {"cds/student_username": username, "cds/name": username}})

    solara.use_memo(_ensure_student_auth, dependencies=[all_cookies])

    BaseSetup(
        remote_api=LOCAL_API,
        global_state=app_state,
        local_state=story_state,
        force_demo=FORCE_DEMO,
    )

    initial_state_loaded = solara.use_reactive(False)

    # Load stored state from the server
    def _state_setup():
        _load_state(app_state, story_state)
        initial_state_loaded.set(True)

    solara.use_memo(_state_setup, dependencies=[])

    initial_state_written = solara.use_reactive(False)

    def _consume_write_state():
        while True:
            if not initial_state_loaded.value:
                time.sleep(2)
                continue

            if not initial_state_written.value:
                logger.info(f"Initializing with full DB write.")
                _write_state(app_state.value.as_dict(), app_state, story_state)
                initial_state_written.set(True)
                continue

            # Retrieve current state
            old_state = app_state.value.as_dict()

            # Sleep for 2 seconds
            time.sleep(2)

            # Retrieve state after sleep
            new_state = app_state.value.as_dict()

            # Get state diff to send atomic updates
            diff = extract_changed_subtree(old_state, new_state)

            # Return if diff dict is empty
            if not diff:
                continue

            # Write the state to the server
            _write_state(diff, app_state, story_state)

    solara.lab.use_task(_consume_write_state, dependencies=[])

    route_restored = solara.use_reactive(False)

    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    route_current, routes_current_level = solara.use_route(peek=True)
    route_index = routes_current_level.index(route_current)

    def _store_user_location():
        if not route_restored.value:
            return

        logger.info(f"Storing path location as `{route_current.path}`")
        # Store the current route index so that users will be returned to their
        #  previous location when they return to the app
        Ref(story_state.fields.last_route).set(f"{route_current.path}")
        Ref(story_state.fields.max_route_index).set(
            max(route_index or 0, story_state.value.max_route_index or 0)
        )

    solara.use_effect(_store_user_location, dependencies=[route_current])

    # TODO: This is a temporary fix to restore the user's location after loading
    #  their state from the database. For some reason, the router resets several
    #  times during this page's rendering, so we just time it out for now.
    def _restore_user_location():
        time.sleep(0.5)
        if not route_restored.value:
            if (
                story_state.value.last_route is not None
                and route_current.path != story_state.value.last_route
            ):
                logger.info(
                    f"Restoring path location to `{story_state.value.last_route}`"
                )
                push_to_route(router, location, story_state.value.last_route)

            route_restored.set(True)

    solara.lab.use_task(_restore_user_location, dependencies=[])

    # The rendering takes a moment while the route resolves, this can appear as
    #  a flicker before the true page loads. Here, we hide the page until the
    #  route is restored.
    if auth.user.value is not None and route_restored.value:
        BaseLayout(
            remote_api=LOCAL_API,
            app_state=app_state,
            story_state=story_state,
            children=children,
            story_name=story_state.value.story_id,
            story_title=story_state.value.title,
        )
