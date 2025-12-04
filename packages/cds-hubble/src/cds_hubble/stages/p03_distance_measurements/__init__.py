import asyncio
from pathlib import Path
from typing import cast

import astropy.units as u
import numpy as np
import solara
import solara.lab
from astropy.coordinates import Angle
from glue_jupyter.app import JupyterApplication
from reacton import ipyvuetify as rv
from solara import Reactive
from solara.lab import computed
from solara.toestand import Ref

from cds_core.base_states import (
    transition_next,
    transition_previous,
    transition_to,
    MultipleChoiceResponse,
)
from cds_core.components import ScaffoldAlert, StateEditor
from cds_core.logger import setup_logger
from cds_core.app_state import AppState
from .stage_state import Marker, StageState
from ...components import (
    AngsizeDosDontsSlideshow,
    DataTable,
    DotplotViewer,
)
from ...helpers.data_management import *
from ...helpers.example_measurement_helpers import assert_example_measurements_in_glue
from ...helpers.measurement_helpers import fill_add_all_measurements, fill_add_wave_vel_ang
from ...helpers.stage_one_and_three_setup import (
    initialize_second_example_measurement,
    _add_or_update_example_measurements_to_glue,
    _glue_setup,
    _update_seed_data_with_examples,
)
from ...helpers.viewer_marker_colors import (
    MY_DATA_COLOR_NAME,
    LIGHT_GENERIC_COLOR,
)
from ...remote import LOCAL_API
from ...story_state import (
    StoryState,
    StudentMeasurement,
    mc_callback,
    get_mc_response,
)
from ...utils import (
    DISTANCE_CONSTANT,
    GALAXY_FOV,
    distance_from_angular_size,
    push_to_route,
    subset_by_label,
    get_image_path,
)
from ...utils import sync_reactives
from ...widgets.distance_tool.distance_tool import DistanceTool

GUIDELINE_ROOT = Path(__file__).parent / "guidelines"
logger = setup_logger("STAGE3")


@solara.component
def DistanceToolComponent(
    galaxy,
    show_ruler,
    angular_size_callback,
    ruler_count_callback,
    use_guard,
    bad_measurement_callback,
    brightness_callback,
    reset_canvas,
    background_counter,
    guard_range,
    on_wwt_ready=None,
):

    wwt_ready = solara.use_reactive(False)
    tool = DistanceTool.element()

    def _on_wwt_ready(ready):
        if ready and (on_wwt_ready is not None):
            on_wwt_ready()

    wwt_ready.subscribe(_on_wwt_ready)

    def set_selected_galaxy():
        widget = solara.get_widget(tool)
        widget.set_background()
        if galaxy:
            widget.measuring = False
            widget.go_to_location(galaxy["ra"], galaxy["decl"], fov=GALAXY_FOV)
        widget.measuring_allowed = bool(galaxy)

    solara.use_effect(set_selected_galaxy, [galaxy])

    def turn_ruler_on():
        widget = solara.get_widget(tool)
        widget.show_ruler = show_ruler

    solara.use_effect(turn_ruler_on, [show_ruler])

    def set_guard(min, max):
        print(f"set_guard: min={min}, max={max}")
        widget = cast(DistanceTool, solara.get_widget(tool))
        widget.set_guard(max=max, min=min)

    solara.use_effect(lambda: set_guard(*guard_range), [guard_range])

    def turn_on_guard():
        widget = cast(DistanceTool, solara.get_widget(tool))
        if use_guard:
            widget.activate_guard()
        else:
            widget.deactivate_guard()

    solara.use_effect(turn_on_guard, [use_guard])

    def _reset_canvas():
        logger.debug("resetting canvas")
        widget = cast(DistanceTool, solara.get_widget(tool))
        widget.reset_canvas()

    solara.use_effect(_reset_canvas, [reset_canvas])

    def _setup_wait_for_ready():
        widget = cast(DistanceTool, solara.get_widget(tool))
        if widget.wwt_ready:
            wwt_ready.set(True)
        else:
            widget.observe(
                lambda change: wwt_ready.set(change["new"]), names="wwt_ready"
            )

    solara.use_effect(_setup_wait_for_ready, [])

    def _define_callbacks():
        widget = cast(DistanceTool, solara.get_widget(tool))

        def update_angular_size(change):
            print(f"update_angular_size: {change['new']}")
            if widget.measuring:
                angle = change["new"]
                if not widget.bad_measurement:
                    angular_size_callback(angle)
                else:
                    bad_measurement_callback()

        widget.observe(update_angular_size, ["angular_size"])

        def get_ruler_click_count(change):
            count = change["new"]
            ruler_count_callback(count)

        widget.observe(get_ruler_click_count, ["ruler_click_count"])

        def update_brightness(change):
            brightness_callback(change["new"])

        widget.observe(update_brightness, ["brightness"])

        background_counter.subscribe(lambda _count: widget.set_background())

    solara.use_effect(_define_callbacks, [wwt_ready.value])


@solara.component
def Page(app_state: Reactive[AppState]):
    story_state = Ref(cast(StoryState, app_state.fields.story_state))
    stage_state = Ref(
        cast(StageState, story_state.fields.stage_states["distance_measurements"])
    )

    # === Setup State Loading and Writing ===
    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    distance_tool_bg_count = solara.use_reactive(0)

    seed_data_setup = solara.use_reactive(False)

    def glue_setup() -> JupyterApplication:
        gjapp = _glue_setup(app_state, story_state)
        if EXAMPLE_GALAXY_SEED_DATA not in gjapp.data_collection:
            logger.error(f"Missing {EXAMPLE_GALAXY_SEED_DATA} in glue data collection.")
        else:
            seed_data_setup.set(True)
        return gjapp

    gjapp = solara.use_memo(glue_setup, dependencies=[])

    example_data_setup = solara.use_reactive(False)

    def add_or_update_example_measurements_to_glue():
        if gjapp is not None:
            _add_or_update_example_measurements_to_glue(story_state, gjapp)
            assert_example_measurements_in_glue(gjapp)
            example_data_setup.set(True)

    second_example_ready = solara.use_reactive(False)

    reset_canvas = solara.use_reactive(1)  # increment to reset canvas

    def _on_marker_updated(marker_new, marker_old):
        # logger.info(f"Marker updated from {marker_old} to {marker_new}")
        if marker_old == Marker.est_dis3:
            _distance_cb(stage_state.value.meas_theta)
            Ref(stage_state.fields.fill_est_dist_values).set(True)

        if marker_new == Marker.dot_seq5:
            # clear the canvas before we get to the second measurement.
            reset_canvas.set(reset_canvas.value + 1)
        if marker_new.is_between(Marker.dot_seq1, Marker.dot_seq4):
            # also don't want to allow changing the measurement
            reset_canvas.set(reset_canvas.value + 1)

        distance_tool_bg_count.set(distance_tool_bg_count.value + 1)

    def _state_callback_setup():
        # We want to minimize duplicate state handling, but also keep the states
        #  independent. We'll set up observers for changes here so that they
        #  automatically keep the states in sync.
        # See Stage 1 for an example of how to do this manually.

        def _on_example_galaxy_selected(*args):
            if stage_state.value.is_current_step(Marker.cho_row1):
                transition_to(stage_state, Marker.ang_siz2)

        selected_example_galaxy = Ref(stage_state.fields.selected_example_galaxy)
        selected_example_galaxy.subscribe(_on_example_galaxy_selected)

        def _on_ruler_clicked_first_time(*args):
            if (
                stage_state.value.is_current_step(Marker.ang_siz3)
                and stage_state.value.ruler_click_count == 1
            ):
                transition_to(stage_state, Marker.ang_siz4)

        ruler_click_count = Ref(stage_state.fields.ruler_click_count)
        ruler_click_count.subscribe(_on_ruler_clicked_first_time)

        def _on_measurement_added(*args):
            if (
                stage_state.value.is_current_step(Marker.ang_siz4)
                and stage_state.value.n_meas == 1
            ):
                transition_to(stage_state, Marker.ang_siz5)

        n_meas = Ref(stage_state.fields.n_meas)
        n_meas.subscribe(_on_measurement_added)

        example_measurements = Ref(story_state.fields.example_measurements)

        def _on_example_measurement_change(meas):
            # make sure the 2nd one is initialized
            initialize_second_example_measurement(story_state)

            # make sure it is in glue
            add_or_update_example_measurements_to_glue()

            # make sure it is in the seed data
            _update_seed_data_with_examples(app_state, gjapp, meas)

        example_measurements.subscribe(_on_example_measurement_change)

        Ref(stage_state.fields.current_step).subscribe_change(_on_marker_updated)

        def show_ruler_range(marker):
            print(f"show_ruler_range: {marker}")
            stage_state.value.show_ruler = marker.is_between(
                Marker.ang_siz3, Marker.est_dis4
            ) or marker.is_between(Marker.dot_seq5, Marker.last())

        Ref(stage_state.fields.current_step).subscribe(show_ruler_range)

    solara.use_effect(_state_callback_setup, dependencies=[])

    def _initialize_state():
        if not story_state.value.measurements_loaded:
            return

        logger.info("Initializing state")

        if stage_state.value.current_step.value >= Marker.cho_row1.value:
            selected_example_galaxy = Ref(stage_state.fields.selected_example_galaxy)

        angular_sizes_total = 0
        for measurement in story_state.value.measurements:
            if measurement.ang_size_value is not None:
                angular_sizes_total += 1
        if stage_state.value.angular_sizes_total != angular_sizes_total:
            Ref(stage_state.fields.angular_sizes_total).set(angular_sizes_total)

        example_angular_sizes_total = 0
        for measurement in story_state.value.example_measurements:
            if measurement.ang_size_value is not None:
                example_angular_sizes_total += 1
        if stage_state.value.example_angular_sizes_total != example_angular_sizes_total:
            Ref(stage_state.fields.example_angular_sizes_total).set(
                example_angular_sizes_total
            )

    solara.use_memo(
        _initialize_state,
        dependencies=[
            Ref(story_state.fields.measurements_loaded).value,
        ],
    )

    def _fill_data_points():
        fill_add_all_measurements(LOCAL_API, story_state, app_state)
        Ref(stage_state.fields.angular_sizes_total).set(5)
        push_to_route(router, location, "explore-data")

    def _fill_thetas():
        fill_add_wave_vel_ang(LOCAL_API, story_state, app_state)
        Ref(stage_state.fields.angular_sizes_total).set(5)

    example_data_setup = solara.use_reactive(False)

    def _init_glue_data_setup():
        if Ref(story_state.fields.measurements_loaded).value:
            add_or_update_example_measurements_to_glue()
            initialize_second_example_measurement(story_state)

    solara.use_effect(
        _init_glue_data_setup,
        dependencies=[Ref(story_state.fields.measurements_loaded).value],
    )

    if app_state.value.show_team_interface:
        with solara.Row():
            with solara.Column():
                StateEditor(
                    Marker,
                    stage_state,
                    story_state,
                    app_state,
                    LOCAL_API,
                    show_all=not app_state.value.educator,
                )
            with solara.Column():
                solara.Button(
                    label="Shortcut: Fill in distance data & Jump to Stage 4",
                    on_click=_fill_data_points,
                    classes=["demo-button"],
                )

    def _update_angular_size(
        update_example: bool,
        galaxy,
        angular_size,
        meas_num="first",
        brightness=1.0,
    ):
        # if bool(galaxy) and angular_size is not None:
        arcsec_value = int(angular_size.to(u.arcsec).value)
        if update_example:
            index = story_state.value.get_example_measurement_index(
                galaxy["id"], measurement_number=meas_num
            )
            if index is not None:
                measurement = Ref(story_state.fields.example_measurements[index])
                measurement.set(
                    measurement.value.model_copy(
                        update={
                            "ang_size_value": arcsec_value,
                            "brightness": brightness,
                        }
                    )
                )
            else:
                raise ValueError(
                    f"Could not find measurement for galaxy {galaxy['id']}"
                )
        else:
            index = story_state.value.get_measurement_index(galaxy["id"])
            if index is not None:
                measurements = story_state.value.measurements
                measurement = story_state.value.measurements[index]
                measurement = measurement.model_copy(
                    update={"ang_size_value": arcsec_value, "brightness": brightness}
                )
                measurements[index] = measurement
                Ref(story_state.fields.measurements).set(measurements)
            else:
                raise ValueError(
                    f"Could not find measurement for galaxy {galaxy['id']}"
                )
        _set_ang_size_total(example=update_example)

    @computed
    def use_second_measurement():
        return Ref(stage_state.fields.current_step).value >= Marker.dot_seq5

    def _update_distance_measurement(
        update_example: bool, galaxy, theta, measurement_number="first"
    ):
        # if bool(galaxy) and theta is not None:
        distance = distance_from_angular_size(theta)
        if update_example:
            index = story_state.value.get_example_measurement_index(
                galaxy["id"], measurement_number=measurement_number
            )
            if index is not None:
                measurements = story_state.value.example_measurements
                measurement = Ref(story_state.fields.example_measurements[index])
                measurement.set(
                    measurement.value.model_copy(update={"est_dist_value": distance})
                )
            else:
                raise ValueError(
                    f"Could not find measurement for galaxy {galaxy['id']}"
                )
        else:
            index = story_state.value.get_measurement_index(galaxy["id"])
            if index is not None:
                measurements = story_state.value.measurements
                measurement = measurements[index]
                measurement = measurement.model_copy(
                    update={"est_dist_value": distance}
                )
                measurements[index] = measurement
                Ref(story_state.fields.measurements).set(measurements)
            else:
                raise ValueError(
                    f"Could not find measurement for galaxy {galaxy['id']}"
                )

    ang_size_dotplot_range = solara.use_reactive([])
    dist_dotplot_range = solara.use_reactive([])
    fill_galaxy_pressed = solara.use_reactive(stage_state.value.distances_total >= 5)
    current_brightness = solara.use_reactive(1.0)

    @computed
    def sync_dotplot_axes():
        return Ref(stage_state.fields.current_step_between).value(
            Marker.dot_seq1, Marker.dot_seq5c
        )

    def setup_zoom_sync():

        sync_reactives(
            ang_size_dotplot_range,
            dist_dotplot_range,
            lambda ang: (
                [(DISTANCE_CONSTANT / max(1, a)) for a in ang][::-1]
                if sync_dotplot_axes.value
                else None
            ),  # angular size to distance
            lambda dist: (
                [(DISTANCE_CONSTANT / max(1, d)) for d in dist][::-1]
                if sync_dotplot_axes.value
                else None
            ),  # distance to angular size
        )

    solara.use_effect(setup_zoom_sync, dependencies=[])

    # Insurance policy
    async def _wwt_ready_timeout():
        await asyncio.sleep(7)
        Ref(stage_state.fields.wwt_ready).set(True)

    solara.lab.use_task(_wwt_ready_timeout)

    @computed
    def example_galaxy_measurement_number():
        if use_second_measurement.value:
            return "second"
        else:
            return "first"

    with solara.ColumnsResponsive(12, large=[4, 8]):
        with rv.Col():
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas1.vue",
                event_back_callback=lambda _: push_to_route(
                    router, location, "distance-introduction"
                ),
                event_next_callback=lambda _: transition_next(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas2.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz2),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas2b.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz2b),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas3.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz3),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas4.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz4),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas5a.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz5a),
                state_view={
                    "dosdonts_tutorial_opened": stage_state.value.dosdonts_tutorial_opened
                },
            )
            # This was skipped in voila version
            # ScaffoldAlert(
            #     GUIDELINE_ROOT / "GuidelineAngsizeMeas6.vue",
            #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
            #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
            #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
            #     show=COMPONENT_STATE.value.is_current_step(Marker.ang_siz6),
            # )

            # the 2nd measurement
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq5.vue",
                # event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(stage_state),
                event_next_callback=lambda _: transition_next(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                scroll_on_mount=False,
                show=stage_state.value.is_current_step(Marker.dot_seq5),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq5b.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq5b),
            )

        with rv.Col():

            @computed
            def on_example_galaxy_marker():
                return Ref(stage_state.fields.current_step).value <= Marker.dot_seq5c

            @computed
            def current_galaxy():
                if on_example_galaxy_marker.value:
                    return Ref(stage_state.fields.selected_example_galaxy).value
                else:
                    return Ref(stage_state.fields.selected_galaxy).value

            @computed
            def current_data():
                return (
                    story_state.value.example_measurements
                    if on_example_galaxy_marker.value
                    else story_state.value.measurements
                )

            def _set_ang_size_total(example: bool):
                total = (
                    Ref(stage_state.fields.example_angular_sizes_total)
                    if on_example_galaxy_marker.value
                    else Ref(stage_state.fields.angular_sizes_total)
                )
                measurements = story_state.value.example_measurements if example else story_state.value.measurements
                num = 0
                for meas in measurements:
                    if meas.ang_size_value is not None:
                        num += 1
                total.set(num)

            def _ang_size_cb(angle):
                """
                Callback for when the angular size is measured. This function
                updates the angular size of the galaxy in the data model and
                puts the measurements in the database.
                """
   
                _update_angular_size(
                    on_example_galaxy_marker.value,
                    current_galaxy.value,
                    angle,
                    example_galaxy_measurement_number.value,
                    brightness=current_brightness.value,
                )

                if on_example_galaxy_marker.value:
                    value = int(angle.to(u.arcsec).value)
                    meas_theta = Ref(stage_state.fields.meas_theta)
                    meas_theta.set(value)
                    n_meas = Ref(stage_state.fields.n_meas)
                    n_meas.set(stage_state.value.n_meas + 1)
                if stage_state.value.bad_measurement:
                    bad_measurement = Ref(stage_state.fields.bad_measurement)
                    bad_measurement.set(False)
                auto_fill_distance = (
                    stage_state.value.current_step_between(
                        Marker.est_dis4, Marker.dot_seq5c
                    )
                    or stage_state.value.current_step.value >= Marker.fil_rem1.value
                    or fill_galaxy_pressed.value
                )
                # the above, but if the student goes back, the distance should update if the distance is already set.
                if on_example_galaxy_marker.value:
                    index = story_state.value.get_example_measurement_index(
                        current_galaxy.value["id"],
                        measurement_number=example_galaxy_measurement_number.value,
                    )
                    if (
                        index is not None
                        and story_state.value.example_measurements[index].est_dist_value
                        is not None
                    ):
                        logger.info(f"autofill the distance of index {index}")
                        auto_fill_distance = True
                if auto_fill_distance:
                    _distance_cb(angle.to(u.arcsec).value)

            def _bad_measurement_cb():
                bad_measurement = Ref(stage_state.fields.bad_measurement)
                bad_measurement.set(True)

            def _distance_cb(theta):
                """
                Callback for when the distance is estimated. This function
                updates the distance of the galaxy in the data model and
                puts the measurements in the database.
                """
                _update_distance_measurement(
                    on_example_galaxy_marker.value,
                    current_galaxy.value,
                    theta,
                    example_galaxy_measurement_number.value,
                )

            def _get_ruler_clicks_cb(count):
                ruler_click_count = Ref(stage_state.fields.ruler_click_count)
                ruler_click_count.set(count)

            def brightness_callback(brightness):
                # logger.info(f'Brightness: {brightness}')
                current_brightness.set(brightness / 100)

            example_guard_range = [Angle("6 arcsec"), Angle("6 arcmin")]
            normal_guard_range = [Angle("6 arcsec"), Angle("60 arcmin")]
            # solara.Button("Reset Canvas", on_click=lambda: reset_canvas.set(reset_canvas.value + 1))
            DistanceToolComponent(
                galaxy=current_galaxy.value,
                show_ruler=stage_state.value.show_ruler,
                angular_size_callback=_ang_size_cb,
                ruler_count_callback=_get_ruler_clicks_cb,
                bad_measurement_callback=_bad_measurement_cb,
                use_guard=True,
                brightness_callback=brightness_callback,
                reset_canvas=reset_canvas.value,
                background_counter=distance_tool_bg_count,
                guard_range=(
                    example_guard_range
                    if on_example_galaxy_marker.value
                    else normal_guard_range
                ),
                on_wwt_ready=lambda: Ref(stage_state.fields.wwt_ready).set(True),
            )

            if stage_state.value.bad_measurement:
                rv.Alert(
                    elevation=2,
                    icon="mdi-alert-circle-outline",
                    prominent=True,
                    dark=True,
                    class_="ma-2 student-warning",
                    children=[
                        "Please try again. This measurement seems to be too large/small. Make sure you are appropriately zoomed in on the galaxy and are measuring the full size."
                    ],
                )

            with rv.Col(cols=6, offset=3):
                if stage_state.value.current_step_at_or_after(Marker.ang_siz5a):
                    dosdonts_tutorial_opened = Ref(
                        stage_state.fields.dosdonts_tutorial_opened
                    )
                    AngsizeDosDontsSlideshow(
                        event_on_dialog_opened=lambda *args: dosdonts_tutorial_opened.set(
                            True
                        ),
                        image_location=get_image_path(router, "stage_two_dos_donts"),
                        show_team_interface=app_state.value.show_team_interface,
                    )

    with solara.ColumnsResponsive(12, large=[4, 8]):
        with rv.Col():
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineChooseRow1.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.cho_row1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAngsizeMeas5.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.ang_siz5),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEstimateDistance1.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.est_dis1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEstimateDistance2.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.est_dis2),
                state_view={"distance_const": DISTANCE_CONSTANT},
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEstimateDistance3.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.est_dis3),
                event_set_distance=_distance_cb,
                state_view={
                    "distance_const": DISTANCE_CONSTANT,
                    "meas_theta": stage_state.value.meas_theta,
                    "fill_values": stage_state.value.fill_est_dist_values,
                },
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEstimateDistance4.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.est_dis4),
                state_view={
                    "distance_const": DISTANCE_CONSTANT,
                    "meas_theta": stage_state.value.meas_theta,
                },
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineRepeatRemainingGalaxies.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.rep_rem1),
                scroll_on_mount=False,
                state_view={
                    "angular_sizes_total": stage_state.value.angular_sizes_total,
                    # TODO: will need to fix this once we have an angular size measurement guard.
                    "bad_angsize": False,
                },
            )
            if (
                stage_state.value.is_current_step(Marker.rep_rem1)
                and app_state.value.show_team_interface
            ):
                solara.Button(
                    label="DEMO SHORTCUT: FILL θ MEASUREMENTS",
                    on_click=_fill_thetas,
                    style="text-transform: none",
                    classes=["demo-button"],
                )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineFillRemainingGalaxies.vue",
                event_next_callback=lambda _: push_to_route(
                    router, location, "explore-data"
                ),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.fil_rem1),
                state_view={"distances_total": stage_state.value.distances_total},
            )

        with rv.Col():
            with rv.Card(class_="pa-0 ma-0", elevation=0):

                distances_total = Ref(stage_state.fields.distances_total)

                def fill_galaxy_distances():
                    dataset = story_state.value.measurements
                    count = 0
                    has_ang_size = all(
                        measurement.ang_size_value is not None
                        for measurement in dataset
                    )
                    if not has_ang_size:
                        logger.error(
                            "\n fill_galaxy_distances: Not all galaxies have angular sizes  \n"
                        )
                    for measurement in dataset:
                        if (
                            measurement.galaxy is not None
                            and measurement.ang_size_value is not None
                        ):
                            count += 1
                            _update_distance_measurement(
                                False,
                                measurement.galaxy.model_dump(),
                                measurement.ang_size_value,
                            )
                        elif measurement.ang_size_value is None:
                            logger.error(
                                f"Galaxy {measurement.galaxy_id} has no angular size"
                            )
                    logger.info(f"fill_galaxy_distances: Filled {count} distances")

                    distances_total.set(count)
                    fill_galaxy_pressed.set(True)

                if (
                    stage_state.value.current_step_at_or_after(Marker.fil_rem1)
                    and app_state.value.show_team_interface
                ):
                    solara.Button(
                        "Demo Shortcut: Fill Galaxy Distances",
                        on_click=lambda: fill_galaxy_distances(),
                        classes=["demo-button"],
                    )

                common_headers = [
                    {
                        "text": "Galaxy ID",
                        "align": "start",
                        "sortable": False,
                        "value": "name",
                    },
                    {"text": "&theta; (arcsec)", "value": "ang_size_value"},
                    {"text": "Distance (Mpc)", "value": "est_dist_value"},
                ]

            if stage_state.value.current_step.value < Marker.rep_rem1.value:

                def update_example_galaxy(galaxy):
                    flag = galaxy.get("value", True)
                    value = galaxy["item"]["galaxy"] if flag else None
                    selected_example_galaxy = Ref(
                        stage_state.fields.selected_example_galaxy
                    )
                    logger.debug(f"selected_example_galaxy: {value}")
                    selected_example_galaxy.set(value)
                    if stage_state.value.is_current_step(Marker.cho_row1):
                        transition_to(stage_state, Marker.ang_siz2)

                @computed
                def selected_example_galaxy_index() -> list:
                    if Ref(stage_state.fields.selected_example_galaxy).value is None:
                        return []
                    if (
                        "id"
                        not in Ref(stage_state.fields.selected_example_galaxy).value
                    ):
                        return []
                    return [0]

                @computed
                def example_galaxy_data():
                    if use_second_measurement.value:
                        return [
                            x.dict()
                            for x in story_state.value.example_measurements
                            if x.measurement_number == "second"
                        ]
                    else:
                        return [
                            x.dict()
                            for x in story_state.value.example_measurements
                            if x.measurement_number == "first"
                        ]

                # DataTable(
                #     title="Example Galaxy",
                #     headers=common_headers + [{ "text": "Measurement Number", "value": "measurement_number" }],
                #     items=[x.dict() for x in local_state.value.example_measurements],
                #     show_select=True,
                #     selected_indices=selected_example_galaxy_index.value,
                #     event_on_row_selected=update_example_galaxy
                # )

                DataTable(
                    title="Example Galaxy",
                    headers=common_headers,
                    items=example_galaxy_data.value,
                    show_select=True,
                    selected_indices=selected_example_galaxy_index.value,
                    event_on_row_selected=update_example_galaxy,
                )

            else:

                def update_galaxy(galaxy):
                    flag = galaxy.get("value", True)
                    value = galaxy["item"]["galaxy"] if flag else None
                    selected_galaxy = Ref(stage_state.fields.selected_galaxy)
                    selected_galaxy.set(value)

                @computed
                def selected_galaxy_index():
                    try:
                        return [
                            story_state.value.get_measurement_index(
                                Ref(stage_state.fields.selected_galaxy).value["id"]
                            )
                        ]
                    except:
                        return []

                @computed
                def table_kwargs():
                    ang_size_tot = Ref(stage_state.fields.angular_sizes_total).value
                    table_data = [
                        s.model_dump(
                            exclude={"galaxy": {"spectrum"}, "measurement_number": True}
                        )
                        for s in Ref(story_state.fields.measurements).value
                    ]
                    return {
                        "title": "My Galaxies",
                        "headers": common_headers,  # + [{ "text": "Measurement Number", "value": "measurement_number" }],
                        "items": table_data,
                        "highlighted": False,  # TODO: Set the markers for this,
                        "event_on_row_selected": update_galaxy,
                        "selected_indices": selected_galaxy_index.value,
                        "show_select": True,
                        "button_icon": "mdi-tape-measure",
                        "button_tooltip": "Calculate & Fill Distances",
                        "show_button": Ref(
                            stage_state.fields.current_step_at_or_after
                        ).value(Marker.fil_rem1),
                        "event_on_button_pressed": lambda _: fill_galaxy_distances(),
                    }

                DataTable(**table_kwargs.value)

    with solara.ColumnsResponsive(12, large=[4, 8]):
        with rv.Col():
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq1.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq1),
                state_view={
                    "color": MY_DATA_COLOR_NAME,
                },
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq2.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq2),
                event_mc_callback=lambda event: mc_callback(
                    event, story_state, stage_state
                ),
                state_view={
                    "mc_score": get_mc_response("ang_meas_consensus", stage_state),
                    "score_tag": "ang_meas_consensus",
                },
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq3.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq3),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq4.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq4),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq4a.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq4a),
                event_mc_callback=lambda event: mc_callback(
                    event, story_state, stage_state
                ),
                state_view={
                    "mc_score": get_mc_response("ang_meas_dist_relation", stage_state),
                    "score_tag": "ang_meas_dist_relation",
                },
            )
            # the 2nd measurement
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq5a.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq5a),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDotplotSeq5c.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dot_seq5c),
            )
            # Not doing the 2nd measurement #dot_seq6 is comparison of 1st and 2nd measurement
            # ScaffoldAlert(
            #     GUIDELINE_ROOT / "GuidelineDotplotSeq6.vue",
            #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
            #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
            #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
            #     show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq6),
            #     event_mc_callback=lambda event: mc_callback(event = event, local_state = local_state, callback=set_mc_scoring),
            #     state_view={'color': MY_DATA_COLOR_NAME, 'mc_score': get_multiple_choice(local_state, 'ang_meas_consensus_2'), 'score_tag': 'ang_meas_consensus_2'}
            # )
            # Not doing the 2nd measurement #dot_seq7 is transition to doing all galaxies. This is not dot_seq5
            # ScaffoldAlert(
            #     GUIDELINE_ROOT / "GuidelineDotplotSeq7.vue",
            #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
            #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
            #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
            #     show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq7),
            # )

        with rv.Col():

            with rv.Card(class_="pa-0 ma-0", elevation=0):

                def set_angular_size_line(points):
                    angular_size_line = Ref(stage_state.fields.angular_size_line)
                    if len(points.xs) > 0:
                        distance = points.xs[0]
                        angular_size = DISTANCE_CONSTANT / distance
                        angular_size_line.set(angular_size)

                def set_distance_line(points):
                    distance_line = Ref(stage_state.fields.distance_line)
                    if len(points.xs) > 0:
                        angular_size = points.xs[0]
                        distance = DISTANCE_CONSTANT / angular_size
                        distance_line.set(distance)

                show_dotplot_lines = Ref(stage_state.fields.show_dotplot_lines)
                if stage_state.value.current_step_at_or_after(Marker.dot_seq4a):
                    show_dotplot_lines.set(True)
                else:
                    show_dotplot_lines.set(False)

                if stage_state.value.current_step_between(
                    Marker.dot_seq1, Marker.dot_seq5c
                ):
                    # solara.Text(f"measurements setup: {measurements_setup.value}")
                    # solara.Text(f"subsets setup: {subsets_setup.value}")
                    if (
                        seed_data_setup.value
                        and example_data_setup.value
                        and EXAMPLE_GALAXY_MEASUREMENTS in gjapp.data_collection
                    ):
                        ignore = []

                        ignore = [gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS]]
                        if stage_state.value.current_step < Marker.dot_seq5:
                            second = subset_by_label(ignore[0], "second measurement")
                            if second is not None:
                                ignore.append(second)
                        else:
                            first = subset_by_label(ignore[0], "first measurement")
                            if first is not None:
                                ignore.append(first)
                        # get angular size dotplot range
                        df1 = (
                            gjapp.data_collection[EXAMPLE_GALAXY_SEED_DATA + "_first"]
                            .to_dataframe()["ang_size_value"]
                            .to_numpy()
                        )
                        df2 = gjapp.data_collection[
                            EXAMPLE_GALAXY_MEASUREMENTS
                        ].to_dataframe()
                        if stage_state.value.current_step < Marker.dot_seq5:
                            df2 = df2[df2["measurement_number"] == "first"][
                                "ang_size_value"
                            ].to_numpy()
                        else:
                            df2 = df2["ang_size_value"].to_numpy()
                        df = np.concatenate((df1, df2))
                        ang_min = np.min(df) * 0.9
                        ang_max = np.max(df) * 1.1

                        def dist_bins(distmin, distmax):
                            if distmin is None or distmax is None:
                                return 64
                            return int(
                                10
                                + 0.3
                                * min(
                                    180,
                                    (
                                        (DISTANCE_CONSTANT / distmin)
                                        - (DISTANCE_CONSTANT / distmax)
                                    ),
                                )
                            )

                        DotplotViewer(
                            gjapp,
                            data=[
                                gjapp.data_collection[
                                    EXAMPLE_GALAXY_SEED_DATA + "_first"
                                ],
                                gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS],
                            ],
                            title="Distance",
                            component_id="est_dist_value",
                            vertical_line_visible=show_dotplot_lines.value,
                            on_vertical_line_visible_changed=show_dotplot_lines.set,
                            line_marker_at=Ref(stage_state.fields.distance_line).value,
                            on_line_marker_at_changed=Ref(
                                stage_state.fields.distance_line
                            ).set,
                            line_marker_color=LIGHT_GENERIC_COLOR,
                            on_click_callback=set_angular_size_line,
                            unit="Mpc",
                            x_label="Distance (Mpc)",
                            y_label="Count",
                            x_bounds=dist_dotplot_range.value,
                            on_x_bounds_changed=dist_dotplot_range.set,
                            hide_layers=ignore,
                            nbin=30,
                            nbin_func=dist_bins,
                            reset_bounds=[
                                DISTANCE_CONSTANT / ang_max,
                                DISTANCE_CONSTANT / ang_min,
                            ],
                        )
                        if stage_state.value.current_step_at_or_after(Marker.dot_seq4):

                            def angsize_bins(angmin, angmax):
                                if angmin is None or angmax is None:
                                    return 64
                                return int(10 + 0.3 * min(180, (angmax - angmin)))

                            DotplotViewer(
                                gjapp,
                                data=[
                                    gjapp.data_collection[
                                        EXAMPLE_GALAXY_SEED_DATA + "_first"
                                    ],
                                    gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS],
                                ],
                                title="Angular Size",
                                component_id="ang_size_value",
                                vertical_line_visible=show_dotplot_lines.value,
                                on_vertical_line_visible_changed=show_dotplot_lines.set,
                                line_marker_at=Ref(
                                    stage_state.fields.angular_size_line
                                ).value,
                                on_line_marker_at_changed=Ref(
                                    stage_state.fields.angular_size_line
                                ).set,
                                line_marker_color=LIGHT_GENERIC_COLOR,
                                on_click_callback=set_distance_line,
                                unit="arcsec",
                                x_label="Angular Size (arcsec)",
                                y_label="Count",
                                x_bounds=ang_size_dotplot_range.value,
                                on_x_bounds_changed=ang_size_dotplot_range.set,
                                hide_layers=ignore,
                                nbin=30,
                                nbin_func=angsize_bins,
                                reset_bounds=[ang_min, ang_max],
                            )
                    else:
                        # raise ValueError("Example galaxy measurements not found in glue data collection")
                        pass
