import asyncio
from pathlib import Path

import numpy as np
import reacton.ipyvuetify as rv
import solara
from glue.core import Data
from glue_jupyter import JupyterApplication
from solara import Reactive
from solara.lab import computed
from solara.toestand import Ref
from typing import cast

from cds_core.base_states import (
    transition_to,
    transition_previous,
    transition_next,
    MultipleChoiceResponse,
)
from cds_core.components import ScaffoldAlert, StateEditor
from cds_core.logger import setup_logger
from cds_core.app_state import AppState
from .stage_state import Marker, StageState
from ...components import (
    SelectionTool,
    DataTable,
    DopplerSlideshow,
    SpectrumViewer,
    SpectrumSlideshow,
    DotplotViewer,
    ReflectVelocitySlideshow,
    DotplotTutorialSlideshow,
)
from ...helpers.data_management import (
    EXAMPLE_GALAXY_SEED_DATA,
    DB_VELOCITY_FIELD,
    EXAMPLE_GALAXY_MEASUREMENTS,
)
from ...helpers.example_measurement_helpers import assert_example_measurements_in_glue
from ...helpers.measurement_helpers import (
    fill_and_add_velocities,
    fill_add_all_measurements,
    fill_and_add_wavelengths,
)
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
    # get_multiple_choice,
    mc_callback,
    get_mc_response,
)
from ...utils import (
    push_to_route,
    velocity_from_wavelengths,
    v2w,
    w2v,
    sync_reactives,
    subset_by_label,
    get_image_path,
)

logger = setup_logger("STAGE")

GUIDELINE_ROOT = Path(__file__).parent / "guidelines"


def is_wavelength_poorly_measured(measwave, restwave, z, tolerance=0.5):
    z_meas = (measwave - restwave) / restwave
    fractional_difference = (((z_meas - z) / z) ** 2) ** 0.5
    return fractional_difference > tolerance


def nbin_func(xmin, xmax):
    if xmin is None or xmax is None:
        return 30
    # full range is 246422.9213488496
    frac_range = (xmax - xmin) / 246423
    max_bins = 100
    min_bins = 30
    power = 1.5  #
    return 30 + int((frac_range**power) * (max_bins - min_bins))


@solara.component
def Page(app_state: Reactive[AppState]):
    story_state = Ref(cast(StoryState, app_state.fields.story_state))
    stage_state = Ref(
        cast(StageState, story_state.fields.stage_states["spectra_&_velocity"])
    )

    selection_tool_candidate_galaxy = solara.use_reactive(None)

    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

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

    def _state_callback_setup():
        # We want to minize duplicate state handling, but also keep the states
        #  independent. We'll set up observers for changes here so that they
        #  automatically keep the states in sync.
        measurements = Ref(story_state.fields.measurements)
        total_galaxies = Ref(stage_state.fields.total_galaxies)
        measurements.subscribe_change(
            lambda *args: total_galaxies.set(len(measurements.value))
        )

        example_measurements = Ref(story_state.fields.example_measurements)

        def _on_example_measurement_change(meas):
            # make sure the 2nd one is initialized
            initialize_second_example_measurement(story_state)

            # make sure it is in glue
            add_or_update_example_measurements_to_glue()

            # make sure it is in the seed data
            _update_seed_data_with_examples(app_state, gjapp, meas)

        example_measurements.subscribe(_on_example_measurement_change)

        def _on_marker_updated(marker):
            if stage_state.value.current_step.value >= Marker.rem_vel1.value:
                initialize_second_example_measurement(
                    story_state
                )  # either set them to current or keep from DB
            if stage_state.value.current_step_between(Marker.mee_gui1, Marker.sel_gal4):
                selection_tool_bg_count.set(selection_tool_bg_count.value + 1)

        Ref(stage_state.fields.current_step).subscribe(_on_marker_updated)

    solara.use_memo(_state_callback_setup, dependencies=[])

    @computed
    def use_second_measurement():
        return Ref(stage_state.fields.current_step).value.value >= Marker.rem_vel1.value

    @computed
    def selected_example_measurement():
        return Ref(story_state.fields.get_example_measurement).value(
            Ref(stage_state.fields.selected_example_galaxy).value,
            measurement_number="second" if use_second_measurement.value else "first",
        )

    @computed
    def selected_measurement():
        return Ref(story_state.fields.get_measurement).value(
            Ref(stage_state.fields.selected_galaxy).value
        )

    def _init_glue_data_setup():
        if Ref(story_state.fields.measurements_loaded).value:
            add_or_update_example_measurements_to_glue()
            initialize_second_example_measurement(story_state)

    solara.use_effect(
        _init_glue_data_setup,
        dependencies=[Ref(story_state.fields.measurements_loaded).value],
    )
    selection_tool_bg_count = solara.use_reactive(0)

    def _fill_galaxies():
        fill_add_all_measurements(LOCAL_API, story_state, app_state)

    def _fill_lambdas():
        fill_and_add_wavelengths(LOCAL_API, story_state, app_state)

    def _fill_stage1_go_stage2():
        fill_and_add_velocities(LOCAL_API, story_state, app_state)
        push_to_route(router, location, f"distance-introduction")

    def _select_random_galaxies():
        need = 5 - len(story_state.value.measurements)
        if need <= 0:
            return
        galaxies: list = LOCAL_API.get_galaxies(story_state)
        sample = np.random.choice(galaxies, size=need, replace=False)
        new_measurements = [
            StudentMeasurement(student_id=app_state.value.student.id, galaxy=galaxy)
            for galaxy in sample
        ]
        measurements = story_state.value.measurements + new_measurements
        Ref(story_state.fields.measurements).set(measurements)

    def _select_one_random_galaxy():
        if len(story_state.value.measurements) >= 5:
            return
        need = 1
        galaxies = LOCAL_API.get_galaxies(story_state)
        rng = np.random.default_rng()
        index = rng.integers(low=0, high=len(galaxies) - 1, size=need)[0]
        galaxy = galaxies[index]
        selection_tool_candidate_galaxy.set(galaxy.model_dump())

    def num_bad_velocities():
        measurements = Ref(story_state.fields.measurements)
        num = 0
        for meas in measurements.value:
            if meas.obs_wave_value is None or meas.rest_wave_value is None:
                # Skip measurements with missing data cuz they have not been attempted
                continue
            elif is_wavelength_poorly_measured(
                meas.obs_wave_value, meas.rest_wave_value, meas.galaxy.z
            ):
                num += 1

        has_multiple_bad_velocities = Ref(
            stage_state.fields.has_multiple_bad_velocities
        )
        has_multiple_bad_velocities.set(num > 1)
        return num

    def set_obs_wave_total():
        obs_wave_total = Ref(stage_state.fields.obs_wave_total)
        measurements = story_state.value.measurements
        num = 0
        for meas in measurements:
            # print(meas)
            if meas.obs_wave_value is not None:
                num += 1
        obs_wave_total.set(num)

    def _initialize_state():
        if stage_state.value.current_step.value == Marker.sel_gal2.value:
            if stage_state.value.total_galaxies == 5:
                transition_to(stage_state, Marker.sel_gal3, force=True)

        if stage_state.value.current_step.value > Marker.cho_row1.value:
            stage_state.value.selected_example_galaxy = (
                1576  # id of the first example galaxy
            )

    solara.use_memo(_initialize_state, dependencies=[])

    def print_selected_galaxy(galaxy):
        print("selected galaxy is now:", galaxy)

    def print_selected_example_galaxy(galaxy):
        print("selected example galaxy is now:", galaxy)

    sync_wavelength_line = solara.use_reactive(6565.0)
    sync_velocity_line = solara.use_reactive(0.0)
    spectrum_bounds = solara.use_reactive([])
    dotplot_bounds = solara.use_reactive([])

    @computed
    def show_synced_lines():
        if not example_data_setup.value:
            return False
        return (
            Ref(stage_state.fields.current_step).value.value >= Marker.dot_seq5.value
            and Ref(stage_state.fields.dotplot_click_count).value > 0
        )

    ## ----- Make sure we are initialized in the correct state ----- ##
    def sync_example_velocity_to_wavelength(velocity):
        if len(story_state.value.example_measurements) > 0:
            lambda_rest = story_state.value.example_measurements[0].rest_wave_value
            lambda_obs = v2w(velocity, lambda_rest)
            logger.debug(
                f"sync_example_velocity_to_wavelength {velocity:0.2f} -> {lambda_obs:0.2f}"
            )
            return lambda_obs
        return None

    def sync_example_wavelength_to_velocity(wavelength):
        if len(story_state.value.example_measurements) > 0:
            lambda_rest = story_state.value.example_measurements[0].rest_wave_value
            velocity = w2v(wavelength, lambda_rest)
            logger.debug(
                f"sync_example_wavelength_to_velocity {wavelength:0.2f} -> {velocity:0.2f}"
            )
            return velocity
        return None

    def sync_spectrum_to_dotplot_range(value):
        if len(story_state.value.example_measurements) > 0:
            logger.debug("Setting dotplot range from spectrum range")
            lambda_rest = story_state.value.example_measurements[0].rest_wave_value
            return [w2v(v, lambda_rest) for v in value]
        return None

    def sync_dotplot_to_spectrum_range(value):
        if len(story_state.value.example_measurements) > 0:
            logger.debug("Setting spectrum range from dotplot range")
            lambda_rest = story_state.value.example_measurements[0].rest_wave_value
            return [v2w(v, lambda_rest) for v in value]
        return None

    def _reactive_subscription_setup():
        Ref(stage_state.fields.selected_galaxy).subscribe(print_selected_galaxy)
        Ref(stage_state.fields.selected_example_galaxy).subscribe(
            print_selected_example_galaxy
        )

        sync_reactives(
            spectrum_bounds,
            dotplot_bounds,
            sync_spectrum_to_dotplot_range,
            sync_dotplot_to_spectrum_range,
        )

    solara.use_effect(_reactive_subscription_setup, dependencies=[])

    def dotplot_click_callback(point):
        Ref(stage_state.fields.dotplot_click_count).set(
            stage_state.value.dotplot_click_count + 1
        )
        sync_velocity_line.set(point.xs[0])
        wavelength = sync_example_velocity_to_wavelength(point.xs[0])
        if wavelength:
            sync_wavelength_line.set(wavelength)

    speech = Ref(app_state.fields.speech)

    if app_state.value.show_team_interface:
        with rv.Row():
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
                    label="Shortcut: Fill in galaxy velocity data & Jump to Stage 2",
                    on_click=_fill_stage1_go_stage2,
                    classes=["demo-button"],
                )
                solara.Button(
                    label="Choose 5 random galaxies",
                    on_click=_select_random_galaxies,
                    classes=["demo-button"],
                )

    with rv.Row():
        with rv.Col(cols=12, lg=4):
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineIntro.vue",
                event_back_callback=lambda _: push_to_route(router, location, "/"),
                event_next_callback=lambda _: transition_next(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.mee_gui1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies1.vue",
                # If at least 1 galaxy has already been selected, we want to go straight from here to sel_gal3.
                event_next_callback=lambda _: transition_to(
                    stage_state,
                    (
                        Marker.sel_gal2
                        if stage_state.value.total_galaxies == 0
                        else Marker.sel_gal3
                    ),
                    force=True,
                ),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.sel_gal1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies2.vue",
                # I think we don't need this next callback because meeting the "next" criteria will autoadvance you to not_gal1 anyway, and then we skip over this guideline if we go backwards from sel_gal3. (But leave it just in case)
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.sel_gal2),
                state_view={
                    "total_galaxies": stage_state.value.total_galaxies,
                    "galaxy_is_selected": stage_state.value.galaxy_is_selected,
                },
                speech=speech.value,
            )

            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies3.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                # You can't get to this marker until at least 1 galaxy has been selected. Once a galaxy has been selected, sel_gal2 doesn't make sense, so jump back to sel_gal1.
                event_back_callback=lambda _: transition_to(
                    stage_state, Marker.sel_gal1, force=True
                ),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.sel_gal3),
                state_view={
                    "total_galaxies": stage_state.value.total_galaxies,
                    "galaxy_is_selected": stage_state.value.galaxy_is_selected,
                },
                speech=speech.value,
            )

            if stage_state.value.is_current_step(
                Marker.sel_gal2
            ) or stage_state.value.is_current_step(Marker.sel_gal3):
                solara.Button(
                    label="Select a random galaxy",
                    on_click=_select_one_random_galaxy,
                    classes=["emergency-button"],
                )

            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies4.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.sel_gal4),
                speech=speech.value,
            )

        with rv.Col(cols=12, lg=8):

            show_snackbar = Ref(story_state.fields.show_snackbar)

            async def snackbar_off(value=None):
                if show_snackbar.value:
                    await asyncio.sleep(3)
                    show_snackbar.set(False)

            solara.lab.use_task(snackbar_off, dependencies=[show_snackbar])

            def _galaxy_added_callback(galaxy_data: dict):
                galaxy = next(
                    gal
                    for gal in LOCAL_API.get_galaxies(story_state)
                    if gal.id == int(galaxy_data["id"])
                )
                already_exists = galaxy.id in [
                    x.galaxy_id for x in story_state.value.measurements
                ]

                if already_exists:
                    return

                if len(story_state.value.measurements) == 5:
                    show_snackbar = Ref(story_state.fields.show_snackbar)
                    snackbar_message = Ref(story_state.fields.snackbar_message)

                    show_snackbar.set(True)
                    snackbar_message.set(
                        "You've already selected 5 galaxies. Continue forth!"
                    )
                    logger.info("Attempted to add more than 5 galaxies.")
                    return

                logger.info("Adding galaxy `%s` to measurements.", galaxy.id)

                measurements = Ref(story_state.fields.measurements)

                measurements.set(
                    measurements.value
                    + [
                        StudentMeasurement(
                            student_id=app_state.value.student.id,
                            galaxy=galaxy,
                        )
                    ]
                )

            total_galaxies = Ref(stage_state.fields.total_galaxies)

            def advance_on_total_galaxies(value):
                if stage_state.value.current_step == Marker.sel_gal2:
                    if value == 1:
                        transition_to(stage_state, Marker.not_gal1)

            total_galaxies.subscribe(advance_on_total_galaxies)

            def _galaxy_selected_callback(galaxy_data: dict):
                galaxy = next(
                    gal
                    for gal in LOCAL_API.get_galaxies(story_state)
                    if gal.id == int(galaxy_data["id"])
                )
                selected_galaxy = Ref(stage_state.fields.selected_galaxy)
                selected_galaxy.set(galaxy.id)
                galaxy_is_selected = Ref(stage_state.fields.galaxy_is_selected)
                galaxy_is_selected.set(True)

            def _deselect_galaxy_callback():
                selected_galaxy = Ref(stage_state.fields.selected_galaxy)
                selected_galaxy.set(None)
                galaxy_is_selected = Ref(stage_state.fields.galaxy_is_selected)
                galaxy_is_selected.set(False)

            show_example_data_table = stage_state.value.current_step_between(
                Marker.cho_row1, Marker.rem_vel1
            )
            selection_tool_measurement = (
                selected_example_measurement
                if show_example_data_table
                else selected_measurement
            )
            selection_tool_galaxy = (
                selection_tool_measurement.value.galaxy.model_dump()
                if (
                    selection_tool_measurement.value is not None
                    and selection_tool_measurement.value.galaxy is not None
                )
                else None
            )

            def _on_wwt_ready_callback():
                Ref(stage_state.fields.wwt_ready).set(True)

            SelectionTool(
                local_state=story_state,
                show_galaxies=stage_state.value.current_step_in(
                    [Marker.sel_gal2, Marker.not_gal1, Marker.sel_gal3]
                ),
                galaxy_selected_callback=_galaxy_selected_callback,
                galaxy_added_callback=_galaxy_added_callback,
                selected_galaxy=selection_tool_galaxy,
                background_counter=selection_tool_bg_count,
                deselect_galaxy_callback=_deselect_galaxy_callback,
                candidate_galaxy=selection_tool_candidate_galaxy.value,
                on_wwt_ready=_on_wwt_ready_callback,
            )

            if show_snackbar.value:
                solara.Info(label=story_state.value.snackbar_message)

    # Measurement Table Row

    with rv.Row():
        with rv.Col(cols=12, lg=4):
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineNoticeGalaxyTable.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                # You can't get to this marker until at least 1 galaxy has been selected. Once a galaxy has been selected, sel_gal2 doesn't make sense, so jump back to sel_gal1.
                event_back_callback=lambda _: transition_to(
                    stage_state, Marker.sel_gal1, force=True
                ),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.not_gal1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineChooseRow.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.cho_row1),
                speech=speech.value,
            )

            validation_4_failed = Ref(
                stage_state.fields.doppler_state.validation_4_failed
            )

            show_values = Ref(stage_state.fields.show_dop_cal4_values)

            def _on_validate_transition(validated):
                logger.debug("Validated transition to dop_cal5: %s", validated)
                validation_4_failed.set(not validated)
                show_values.set(validated)
                if not validated:
                    return

                if validated:
                    transition_to(stage_state, Marker.dop_cal5)

                show_doppler_dialog = Ref(stage_state.fields.show_doppler_dialog)
                logger.debug("Setting show_doppler_dialog to %s", validated)
                show_doppler_dialog.set(validated)

            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDopplerCalc4.vue",
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.current_step_in(
                    [Marker.dop_cal4, Marker.dop_cal5]
                ),
                state_view={
                    "lambda_obs": round(stage_state.value.obs_wave),
                    "lambda_rest": (
                        selected_example_measurement.value.rest_wave_value
                        if selected_example_measurement.value is not None
                        else None
                    ),
                    "failed_validation_4": validation_4_failed.value,
                    "fill_values": show_values.value,
                },
                event_on_validate_transition=_on_validate_transition,
                speech=speech.value,
            )

            # This whole slideshow is basically dop_cal5
            if stage_state.value.is_current_step(Marker.dop_cal5):
                show_doppler_dialog = Ref(stage_state.fields.show_doppler_dialog)
                step = Ref(stage_state.fields.doppler_state.step)
                validation_5_failed = Ref(
                    stage_state.fields.doppler_state.validation_5_failed
                )
                max_step_completed_5 = Ref(
                    stage_state.fields.doppler_state.max_step_completed_5
                )
                student_c = Ref(stage_state.fields.doppler_state.student_c)
                velocity_calculated = Ref(
                    stage_state.fields.doppler_state.velocity_calculated
                )

                def _velocity_calculated_callback(value):
                    example_measurement_index = (
                        story_state.value.get_example_measurement_index(
                            stage_state.value.selected_example_galaxy,
                            measurement_number="first",
                        )
                    )
                    if example_measurement_index is None:
                        return
                    example_measurement = Ref(
                        story_state.fields.example_measurements[
                            example_measurement_index
                        ]
                    )
                    example_measurement.set(
                        example_measurement.value.model_copy(
                            update={"velocity_value": round(value)}
                        )
                    )

                DopplerSlideshow(
                    dialog=stage_state.value.show_doppler_dialog,
                    titles=stage_state.value.doppler_state.titles,
                    step=stage_state.value.doppler_state.step,
                    length=stage_state.value.doppler_state.length,
                    lambda_obs=round(stage_state.value.obs_wave),
                    lambda_rest=(
                        selected_example_measurement.value.rest_wave_value
                        if selected_example_measurement.value is not None
                        else None
                    ),
                    max_step_completed_5=stage_state.value.doppler_state.max_step_completed_5,
                    failed_validation_5=stage_state.value.doppler_state.validation_5_failed,
                    interact_steps_5=stage_state.value.doppler_state.interact_steps_5,
                    student_c=stage_state.value.doppler_state.student_c,
                    student_vel_calc=stage_state.value.doppler_state.velocity_calculated,
                    event_set_dialog=show_doppler_dialog.set,
                    event_set_step=step.set,
                    event_set_failed_validation_5=validation_5_failed.set,
                    event_set_max_step_completed_5=max_step_completed_5.set,
                    event_set_student_vel_calc=velocity_calculated.set,
                    event_set_student_vel=_velocity_calculated_callback,
                    event_set_student_c=student_c.set,
                    event_back_callback=lambda _: transition_previous(stage_state),
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "mc_score": get_mc_response("interpret-velocity", stage_state),
                        "score_tag": "interpret-velocity",
                    },
                    show_team_interface=app_state.value.show_team_interface,
                )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineCheckMeasurement.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: _on_validate_transition(
                    True
                ),  # Send user back to dop_cal5 and open dialog
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.che_mea1),
                speech=speech.value,
            )
            # Skip for now since we aren't offering 2nd measurement.
            # ScaffoldAlert(
            #     GUIDELINE_ROOT / "GuidelineDotSequence13.vue",
            #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
            #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
            #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
            #     show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq13),
            # )
            set_obs_wave_total()
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineRemainingGals.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.rem_gal1),
                state_view={
                    "obswaves_total": stage_state.value.obs_wave_total,
                    "has_bad_velocities": stage_state.value.has_bad_velocities,
                    "has_multiple_bad_velocities": stage_state.value.has_multiple_bad_velocities,
                    "selected_galaxy": (
                        selected_measurement.value.dict()
                        if selected_measurement.value is not None
                        else None
                    ),
                },
                speech=speech.value,
            )
            if app_state.value.show_team_interface:
                if stage_state.value.is_current_step(Marker.rem_gal1):
                    solara.Button(
                        label="DEMO SHORTCUT: FILL λ MEASUREMENTS",
                        on_click=_fill_lambdas,
                        style="text-transform: none;",
                        classes=["demo-button"],
                    )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDopplerCalc6.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.dop_cal6),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineReflectVelValues.vue",
                event_next_callback=lambda _: transition_next(stage_state),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                event_mc_callback=lambda event: mc_callback(
                    event, story_state, stage_state
                ),
                show=stage_state.value.is_current_step(Marker.ref_vel1),
                state_view={
                    "mc_score": get_mc_response("reflect_vel_value", stage_state),
                    "score_tag": "reflect_vel_value",
                },
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEndStage1.vue",
                event_next_callback=lambda _: push_to_route(
                    router, location, "distance-introduction"
                ),
                event_back_callback=lambda _: transition_previous(stage_state),
                can_advance=stage_state.value.can_transition(next=True),
                show=stage_state.value.is_current_step(Marker.end_sta1),
                state_view={
                    "has_bad_velocities": stage_state.value.has_bad_velocities,
                    "has_multiple_bad_velocities": stage_state.value.has_multiple_bad_velocities,
                },
                speech=speech.value,
            )

        with rv.Col(cols=12, lg=8):
            show_example_data_table = stage_state.value.current_step_between(
                Marker.cho_row1, Marker.rem_vel1
            )

            if show_example_data_table:
                selected_example_galaxy = Ref(
                    stage_state.fields.selected_example_galaxy
                )

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

                @computed
                def selected_example_galaxy_index():
                    index = story_state.value.get_example_measurement_index(
                        selected_example_galaxy.value,
                        measurement_number=(
                            "second" if use_second_measurement.value else "first"
                        ),
                    )
                    if index is None:
                        return []
                    else:
                        return [0]

                def update_example_galaxy(galaxy):
                    flag = galaxy.get("value", True)
                    value = galaxy["item"]["galaxy_id"] if flag else None
                    selected_example_galaxy = Ref(
                        stage_state.fields.selected_example_galaxy
                    )
                    if value is not None:
                        galaxy = story_state.value.get_example_measurement(
                            value,
                            measurement_number=(
                                "second" if use_second_measurement.value else "first"
                            ),
                        )
                        if galaxy is not None:
                            value = galaxy.galaxy_id
                        else:
                            value = None

                    selected_example_galaxy.set(value)

                common_headers = [
                    {
                        "text": "Galaxy ID",
                        "align": "start",
                        "sortable": False,
                        "value": "name",
                    },
                    {"text": "Element", "value": "element"},
                    {
                        "text": "&lambda;<sub>rest</sub> (&Aring;)",
                        "value": "rest_wave_value",
                    },
                    {
                        "text": "&lambda;<sub>obs</sub> (&Aring;)",
                        "value": "obs_wave_value",
                    },
                    {"text": "Velocity (km/s)", "value": "velocity_value"},
                ]
                if use_second_measurement.value:
                    measnum_header = {
                        "text": "Measurement",
                        "value": "measurement_number",
                    }
                    common_headers.append(measnum_header)

                # with solara.Card(title="Remove: for testing", style={'background-color': 'var(--warning-dark)'}):
                #     solara.Text(f"{COMPONENT_STATE.value.obs_wave}")
                #     DataTable(title="Example Measurements",
                #             items=[x.model_dump() for x in local_state.value.example_measurements])

                DataTable(
                    title="Example Galaxy",
                    headers=common_headers,
                    items=example_galaxy_data.value,
                    selected_indices=selected_example_galaxy_index.value,
                    show_select=stage_state.value.current_step_at_or_after(
                        Marker.cho_row1
                    ),
                    event_on_row_selected=update_example_galaxy,
                )
            else:
                selected_galaxy = Ref(stage_state.fields.selected_galaxy)

                def _on_table_row_selected(row):
                    galaxy_measurement = story_state.value.get_measurement(
                        row["item"]["galaxy_id"]
                    )
                    if galaxy_measurement is not None:
                        selected_galaxy.set(galaxy_measurement.galaxy_id)

                    obs_wave = Ref(stage_state.fields.obs_wave)
                    obs_wave.set(0)

                def _on_calculate_velocity():
                    for i in range(len(story_state.value.measurements)):
                        measurement = Ref(story_state.fields.measurements[i])
                        velocity = round(
                            3e5
                            * (
                                measurement.value.obs_wave_value
                                / measurement.value.rest_wave_value
                                - 1
                            )
                        )
                        measurement.set(
                            measurement.value.model_copy(
                                update={"velocity_value": velocity}
                            )
                        )

                        velocities_total = Ref(stage_state.fields.velocities_total)
                        velocities_total.set(velocities_total.value + 1)

                @computed
                def selected_galaxy_index():
                    index = story_state.value.get_measurement_index(
                        selected_galaxy.value
                    )
                    if index is None:
                        return []
                    else:
                        return [index]

                DataTable(
                    title="My Galaxies",
                    items=[x.dict() for x in story_state.value.measurements],
                    selected_indices=selected_galaxy_index.value,
                    show_select=stage_state.value.current_step_at_or_after(
                        Marker.cho_row1
                    ),
                    button_icon="mdi-run-fast",
                    button_tooltip="Calculate & Fill Velocities",
                    show_button=stage_state.value.is_current_step(Marker.dop_cal6),
                    event_on_row_selected=_on_table_row_selected,
                    event_on_button_pressed=lambda _: _on_calculate_velocity(),
                )

    # dot plot slideshow button row

    if stage_state.value.current_step_between(Marker.int_dot1, Marker.rem_vel1):
        with rv.Row(class_="no-padding"):
            with rv.Col(cols=12, lg=4, class_="no-padding"):
                pass
            with rv.Col(cols=12, lg=8, class_="no-padding"):
                with rv.Col(cols=4, offset=4, class_="no-padding"):
                    dotplot_tutorial_finished = Ref(
                        stage_state.fields.dotplot_tutorial_finished
                    )

                    tut_viewer_data = None
                    if EXAMPLE_GALAXY_SEED_DATA + "_tutorial" in gjapp.data_collection:
                        tut_viewer_data: Data = gjapp.data_collection[
                            EXAMPLE_GALAXY_SEED_DATA + "_tutorial"
                        ]
                    # solara.Markdown(tut_viewer_data.to_dataframe().to_markdown())
                    DotplotTutorialSlideshow(
                        dialog=stage_state.value.show_dotplot_tutorial_dialog,
                        step=stage_state.value.dotplot_tutorial_state.step,
                        length=stage_state.value.dotplot_tutorial_state.length,
                        max_step_completed=stage_state.value.dotplot_tutorial_state.max_step_completed,
                        dotplot_viewer=DotplotViewer(
                            gjapp,
                            data=tut_viewer_data,
                            component_id=DB_VELOCITY_FIELD,
                            vertical_line_visible=False,
                            line_marker_color=LIGHT_GENERIC_COLOR,
                            unit="km / s",
                            x_label="Velocity (km/s)",
                            y_label="Count",
                            nbin=20,
                        ),
                        event_tutorial_finished=lambda _: dotplot_tutorial_finished.set(
                            True
                        ),
                        event_show_dialog=lambda v: Ref(
                            stage_state.fields.show_dotplot_tutorial_dialog
                        ).set(v),
                        event_set_step=Ref(
                            stage_state.fields.dotplot_tutorial_state.step
                        ).set,
                        show_team_interface=app_state.value.show_team_interface,
                    )

    # Dot Plot 1st measurement row
    if stage_state.value.current_step_between(Marker.int_dot1, Marker.rem_vel1):
        with rv.Row(class_="no-y-padding"):
            with rv.Col(cols=12, lg=4, class_="no-y-padding"):
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineIntroDotplot.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.int_dot1),
                    speech=speech.value,
                    state_view={"color": MY_DATA_COLOR_NAME},
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence01.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq1),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence02.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq2),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence03.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq3),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence04a.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq4a),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence05.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq5),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence06.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq6),
                    speech=speech.value,
                    event_zoom_to_range=lambda event: dotplot_bounds.set([9000, 13500]),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence07.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq7),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence08.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    event_zoom_to_range=lambda event: dotplot_bounds.set([9000, 13500]),
                    show=stage_state.value.is_current_step(Marker.dot_seq8),
                    state_view={
                        "mc_score": get_mc_response("vel_meas_consensus", stage_state),
                        "score_tag": "vel_meas_consensus",
                    },
                    speech=speech.value,
                )

            if stage_state.value.current_step_between(Marker.int_dot1, Marker.rem_vel1):
                with rv.Col(cols=12, lg=8, class_="no-y-padding"):

                    if (
                        EXAMPLE_GALAXY_MEASUREMENTS in gjapp.data_collection
                        and len(story_state.value.example_measurements) > 0
                        and example_data_setup.value
                    ):
                        viewer_data = [
                            gjapp.data_collection[EXAMPLE_GALAXY_SEED_DATA + "_first"],
                            gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS],
                        ]

                        ignore = [gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS]]
                        if (
                            stage_state.value.current_step.value
                            != Marker.rem_vel1.value
                        ):
                            ignore += [
                                subset_by_label(
                                    gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS],
                                    "second measurement",
                                )
                            ]
                        else:
                            ignore += [
                                subset_by_label(
                                    gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS],
                                    "first measurement",
                                )
                            ]

                        DotplotViewer(
                            gjapp,
                            title="Dotplot: Example Galaxy Velocities",
                            data=viewer_data,
                            component_id=DB_VELOCITY_FIELD,
                            vertical_line_visible=show_synced_lines.value,
                            line_marker_at=sync_velocity_line.value,
                            line_marker_color=LIGHT_GENERIC_COLOR,
                            on_click_callback=dotplot_click_callback,
                            unit="km / s",
                            x_label="Velocity (km/s)",
                            y_label="Count",
                            nbin=30,
                            nbin_func=nbin_func,
                            x_bounds=dotplot_bounds.value,
                            on_x_bounds_changed=dotplot_bounds.set,
                            reset_bounds=list(
                                map(
                                    sync_example_wavelength_to_velocity,
                                    # bounds of example galaxy spectrum
                                    [3796.6455078125, 9187.5576171875],
                                )
                            ),
                            hide_layers=ignore,  # type: ignore
                        )

    # Spectrum Viewer row
    if (
        stage_state.value.current_step_between(Marker.mee_spe1, Marker.che_mea1)
        or stage_state.value.current_step_between(Marker.dot_seq4, Marker.rem_vel1)
        or stage_state.value.current_step_at_or_after(Marker.rem_gal1)
    ):
        with rv.Row():
            with rv.Col(cols=12, lg=4):
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineSpectrum.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.mee_spe1),
                    state_view={
                        "spectrum_tutorial_opened": stage_state.value.spectrum_tutorial_opened
                    },
                    speech=speech.value,
                )

                selected_example_galaxy_data = (
                    selected_example_measurement.value.galaxy.dict()
                    if selected_example_measurement.value is not None
                    else None
                )

                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineRestwave.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.res_wav1),
                    state_view={
                        "selected_example_galaxy": selected_example_galaxy_data,
                        "lambda_on": stage_state.value.rest_wave_tool_activated,
                    },
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineObswave1.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.obs_wav1),
                    state_view={
                        "selected_example_galaxy": selected_example_galaxy_data
                    },
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineObswave2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.obs_wav2),
                    state_view={
                        "selected_example_galaxy": selected_example_galaxy_data,
                        "zoom_tool_activated": stage_state.value.zoom_tool_activated,
                        "zoom_tool_active": stage_state.value.zoom_tool_active,
                    },
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDopplerCalc0.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dop_cal0),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDopplerCalc2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dop_cal2),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence04.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq4),
                    speech=speech.value,
                    state_view={
                        "color": MY_DATA_COLOR_NAME,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence10.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq10),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence11.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.dot_seq11),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineRemeasureVelocity.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.rem_vel1),
                    speech=speech.value,
                )
                # ScaffoldAlert(
                #     GUIDELINE_ROOT / "GuidelineDotSequence13a.vue",
                #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
                #     show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq13a),
                #     speech=speech.value,
                # )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineReflectOnData.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.ref_dat1),
                    speech=speech.value,
                )

            with rv.Col(cols=12, lg=8):
                show_example_spectrum = stage_state.value.current_step_between(
                    Marker.mee_spe1, Marker.che_mea1
                ) or stage_state.value.current_step_between(
                    Marker.dot_seq4, Marker.rem_vel1
                )

                show_galaxy_spectrum = stage_state.value.current_step_at_or_after(
                    Marker.rem_gal1
                )

                if show_example_spectrum:

                    def _example_wavelength_measured_callback(value):
                        example_measurement_index = (
                            story_state.value.get_example_measurement_index(
                                stage_state.value.selected_example_galaxy,
                                measurement_number=(
                                    "second"
                                    if use_second_measurement.value
                                    else "first"
                                ),
                            )
                        )
                        if example_measurement_index is None:
                            return

                        example_measurements = story_state.value.example_measurements
                        example_measurement = Ref(
                            story_state.fields.example_measurements[
                                example_measurement_index
                            ]
                        )

                        obs_wave = Ref(stage_state.fields.obs_wave)
                        obs_wave.set(value)

                        if example_measurement.value.velocity_value is None:
                            example_measurement.set(
                                example_measurement.value.model_copy(
                                    update={"obs_wave_value": round(value)}
                                )
                            )
                        else:
                            velocity = velocity_from_wavelengths(
                                value, example_measurement.value.rest_wave_value
                            )
                            example_measurement.set(
                                example_measurement.value.model_copy(
                                    update={
                                        "obs_wave_value": round(value),
                                        "velocity_value": velocity,
                                    }
                                )
                            )
                        # example_measurements[example_measurement_index] = example_measurement.value
                        # Ref(local_state.fields.example_measurements).set(example_measurements)
                        obs_wave_tool_used.set(True)
                        # obs_wave = Ref(COMPONENT_STATE.fields.obs_wave)
                        # obs_wave.set(value)

                    def _on_set_marker_location(value):
                        logger.debug("Setting marker location spectrum -> dotplot")
                        velocity = sync_example_wavelength_to_velocity(value)
                        if velocity:
                            logger.debug(f"Setting velocity {velocity: 0.2f} ")
                            sync_velocity_line.set(velocity)

                    obs_wave_tool_used = Ref(stage_state.fields.obs_wave_tool_used)
                    rest_wave_tool_activated = Ref(
                        stage_state.fields.rest_wave_tool_activated
                    )
                    zoom_tool_activated = Ref(stage_state.fields.zoom_tool_activated)
                    zoom_tool_active = Ref(stage_state.fields.zoom_tool_active)

                    @computed
                    def obs_wav_marker_value():
                        meas = story_state.value.example_measurements
                        if story_state.value.measurements_loaded and len(meas) > 0:
                            step = stage_state.value.current_step.value
                            if (
                                step >= Marker.rem_vel1.value
                                and meas[1].obs_wave_value is not None
                            ):
                                return meas[1].obs_wave_value
                            elif (
                                step >= Marker.dot_seq1.value
                                and meas[0].velocity_value is not None
                            ):
                                return meas[0].obs_wave_value
                        return stage_state.value.obs_wave

                    def _on_zoom():
                        zoom_tool_activated.set(True)
                        zoom_tool_active.set(True)

                    def _on_reset():
                        zoom_tool_active.set(False)

                    SpectrumViewer(
                        galaxy_data=(
                            selected_example_measurement.value.galaxy
                            if selected_example_measurement.value is not None
                            else None
                        ),
                        obs_wave=obs_wav_marker_value.value,  # COMPONENT_STATE.value.obs_wave if COMPONENT_STATE.value.current_step < Marker.dot_seq1 else E,
                        spectrum_click_enabled=(
                            stage_state.value.current_step_between(
                                Marker.obs_wav1, Marker.obs_wav2
                            )
                            or stage_state.value.current_step.value
                            == Marker.rem_vel1.value
                        ),
                        on_obs_wave_measured=_example_wavelength_measured_callback,
                        on_rest_wave_tool_clicked=lambda: rest_wave_tool_activated.set(
                            True
                        ),
                        on_zoom=_on_zoom,
                        on_reset_tool_clicked=_on_reset,
                        marker_position=(
                            sync_wavelength_line if show_synced_lines.value else None
                        ),
                        spectrum_bounds=spectrum_bounds,  # type: ignore
                        show_obs_wave_line=stage_state.value.current_step_at_or_after(
                            Marker.dot_seq4
                        ),
                        on_set_marker_position=_on_set_marker_location,
                        local_state=story_state,
                    )

                elif show_galaxy_spectrum:

                    def _wavelength_measured_callback(value):
                        measurement_index = story_state.value.get_measurement_index(
                            stage_state.value.selected_galaxy
                        )
                        if measurement_index is None:
                            return

                        has_bad_velocities = Ref(stage_state.fields.has_bad_velocities)
                        is_bad = is_wavelength_poorly_measured(
                            value,
                            selected_measurement.value.rest_wave_value,
                            selected_measurement.value.galaxy.z,
                        )
                        has_bad_velocities.set(is_bad)
                        num_bad_velocities()

                        if not is_bad:

                            obs_wave = Ref(stage_state.fields.obs_wave)
                            obs_wave.set(value)

                            measurement = Ref(
                                story_state.fields.measurements[measurement_index]
                            )

                            if measurement.value.velocity_value is None:
                                measurement.set(
                                    measurement.value.model_copy(
                                        update={"obs_wave_value": round(value)}
                                    )
                                )

                            else:
                                velocity = velocity_from_wavelengths(
                                    value, measurement.value.rest_wave_value
                                )
                                measurement.set(
                                    measurement.value.model_copy(
                                        update={
                                            "obs_wave_value": round(value),
                                            "velocity_value": velocity,
                                        }
                                    )
                                )

                            set_obs_wave_total()

                        else:
                            logger.info("Wavelength measurement is bad")

                    if stage_state.value.has_bad_velocities:
                        rv.Alert(
                            elevation=2,
                            icon="mdi-alert-circle-outline",
                            prominent=True,
                            dark=True,
                            class_="ma-2 student-warning",
                            children=[
                                "Your measured wavelength value is not within the expected range. Please try again. Ask your instructor if you are not sure where to measure."
                            ],
                        )

                    SpectrumViewer(
                        galaxy_data=(
                            selected_measurement.value.galaxy
                            if selected_measurement.value is not None
                            else None
                        ),
                        obs_wave=stage_state.value.obs_wave,
                        spectrum_click_enabled=stage_state.value.current_step_at_or_after(
                            Marker.obs_wav1
                        ),
                        on_obs_wave_measured=_wavelength_measured_callback,
                        local_state=story_state,
                    )
                if stage_state.value.current_step_between(
                    Marker.mee_spe1, Marker.rem_gal1
                ):  # center single button
                    with rv.Row():
                        with rv.Col(cols=4, offset=4):
                            spectrum_tutorial_opened = Ref(
                                stage_state.fields.spectrum_tutorial_opened
                            )
                            SpectrumSlideshow(
                                event_dialog_opened_callback=lambda _: spectrum_tutorial_opened.set(
                                    True
                                ),
                                image_location=get_image_path(
                                    router, "stage_one_spectrum"
                                ),
                                show_team_interface=app_state.value.show_team_interface,
                            )

                if stage_state.value.current_step_at_or_after(
                    Marker.ref_dat1
                ):  # space 2 buttons nicely
                    with rv.Row():
                        with rv.Col(cols=4, offset=2):
                            SpectrumSlideshow(
                                image_location=get_image_path(
                                    router, "stage_one_spectrum"
                                ),
                                show_team_interface=app_state.value.show_team_interface,
                            )
                        with rv.Col(cols=4):
                            show_reflection_dialog = Ref(
                                stage_state.fields.show_reflection_dialog
                            )
                            reflect_step = Ref(
                                stage_state.fields.velocity_reflection_state.step
                            )
                            reflect_max_step_completed = Ref(
                                stage_state.fields.velocity_reflection_state.max_step_completed
                            )
                            reflection_complete = Ref(
                                stage_state.fields.reflection_complete
                            )

                            ReflectVelocitySlideshow(
                                length=8,
                                titles=[
                                    "Reflect on your data",
                                    "What would a 1920's scientist wonder?",
                                    "Observed vs. rest wavelengths",
                                    "How galaxies move",
                                    "Do your data agree with 1920's thinking?",
                                    "Do your data agree with 1920's thinking?",
                                    "Did your peers find what you found?",
                                    "Reflection complete",
                                ],
                                interact_steps=[2, 3, 4, 5, 6],
                                require_responses=True,
                                dialog=stage_state.value.show_reflection_dialog,
                                step=stage_state.value.velocity_reflection_state.step,
                                max_step_completed=stage_state.value.velocity_reflection_state.max_step_completed,
                                reflection_complete=stage_state.value.reflection_complete,
                                state_view={
                                    "mc_score_2": get_mc_response(
                                        "wavelength-comparison", stage_state
                                    ),
                                    "score_tag_2": "wavelength-comparison",
                                    "mc_score_3": get_mc_response(
                                        "galaxy-motion", stage_state
                                    ),
                                    "score_tag_3": "galaxy-motion",
                                    "mc_score_4": get_mc_response(
                                        "steady-state-consistent", stage_state
                                    ),
                                    "score_tag_4": "steady-state-consistent",
                                    "mc_score_5": get_mc_response(
                                        "moving-randomly-consistent", stage_state
                                    ),
                                    "score_tag_5": "moving-randomly-consistent",
                                    "mc_score_6": get_mc_response(
                                        "peers-data-agree", stage_state
                                    ),
                                    "score_tag_6": "peers-data-agree",
                                },
                                event_set_dialog=show_reflection_dialog.set,
                                event_mc_callback=lambda event: mc_callback(
                                    event, story_state, stage_state
                                ),
                                # These are numbered based on window-item value
                                event_set_step=reflect_step.set,
                                event_set_max_step_completed=reflect_max_step_completed.set,
                                event_on_reflection_complete=lambda _: reflection_complete.set(
                                    True
                                ),
                                show_team_interface=app_state.value.show_team_interface,
                            )
