import solara
from solara.lab import computed
from ...state import LOCAL_STATE, GLOBAL_STATE, get_multiple_choice, mc_callback
from .component_state import COMPONENT_STATE, Marker
from ...remote import LOCAL_API
from glue_jupyter import JupyterApplication
import asyncio
from pathlib import Path
from cds_core.components import ScaffoldAlert, StateEditor
import reacton.ipyvuetify as rv
from ...base_component_state import (
    transition_to,
    transition_previous,
    transition_next,
)
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
from ...state import GalaxyData, StudentMeasurement
from ...viewer_marker_colors import MY_DATA_COLOR, MY_DATA_COLOR_NAME, LIGHT_GENERIC_COLOR, GENERIC_COLOR

# from solara.lab import Ref
from solara.toestand import Ref
from cds_core.logger import setup_logger
from ...data_management import (
    EXAMPLE_GALAXY_SEED_DATA,
    DB_VELOCITY_FIELD,
    EXAMPLE_GALAXY_MEASUREMENTS,
    DB_MEASWAVE_FIELD,
    STUDENT_ID_COMPONENT,
)
import numpy as np
from glue.core import Data
from ...utils import (
    models_to_glue_data,
    push_to_route, 
    velocity_from_wavelengths, 
    v2w, w2v, sync_reactives,
    _add_or_update_data,
    _add_link,
    subset_by_label,
    get_image_path,
)
from ...example_measurement_helpers import (
    assert_example_measurements_in_glue
)

from ...stage_one_and_three_setup import (
    initialize_second_example_measurement,
    _add_or_update_example_measurements_to_glue,
    _glue_setup,
    _update_seed_data_with_examples,
)

from cds_hubble.measurement_helpers import (
    fill_add_all_measurements,
    fill_and_add_wavelengths,
    fill_and_add_velocities,
)

logger = setup_logger("STAGE")

GUIDELINE_ROOT = Path(__file__).parent / "guidelines"


def is_wavelength_poorly_measured(measwave, restwave, z, tolerance = 0.5):
    z_meas =  (measwave - restwave) / restwave
    fractional_difference = (((z_meas - z) / z)** 2)**0.5
    return fractional_difference > tolerance


def nbin_func(xmin, xmax):
    if xmin is None or xmax is None:
        return 30
    # full range is 246422.9213488496
    frac_range = (xmax - xmin) / 246423
    max_bins = 100
    min_bins = 30
    power = 1.5 # 
    return 30 + int((frac_range ** power) * (max_bins - min_bins))


@solara.component
def Page():
    solara.Title("HubbleDS")

    loaded_component_state = solara.use_reactive(False)
    selection_tool_candidate_galaxy = solara.use_reactive(None)

    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    def _load_component_state():
        # Load stored component state from database, measurement data is
        #   considered higher-level and is loaded when the story starts.
        LOCAL_API.get_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)

        total_galaxies = Ref(COMPONENT_STATE.fields.total_galaxies)

        if len(LOCAL_STATE.value.measurements) != total_galaxies.value:
            logger.error(
                "Detected mismatch between stored measurements and current "
                f"recorded number of galaxies. Stored: {len(LOCAL_STATE.value.measurements)}, "
                f"Current: {total_galaxies.value}."
            )
            total_galaxies.set(len(LOCAL_STATE.value.measurements))

        logger.info("Finished loading component state.")
        loaded_component_state.set(True)

    solara.use_memo(_load_component_state, dependencies=[])

    def _write_component_state():
        if not loaded_component_state.value:
            return

        # Listen for changes in the states and write them to the database
        res = LOCAL_API.put_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)
        if res:
            logger.info("Wrote component state to database.")
        else:
            logger.info("Did not write component state to database.")

    solara.lab.use_task(_write_component_state, dependencies=[COMPONENT_STATE.value])
    
    seed_data_setup = solara.use_reactive(False)
    def glue_setup() -> JupyterApplication:
        gjapp = _glue_setup()
        if EXAMPLE_GALAXY_SEED_DATA not in gjapp.data_collection:
            logger.error(
                f"Missing {EXAMPLE_GALAXY_SEED_DATA} in glue data collection."
            )
        else:
            seed_data_setup.set(True)
        return gjapp
    

    gjapp = solara.use_memo(glue_setup, dependencies=[])
    
    example_data_setup = solara.use_reactive(False)
    def add_or_update_example_measurements_to_glue():
        if (gjapp is not None):
            _add_or_update_example_measurements_to_glue(gjapp)
            assert_example_measurements_in_glue(gjapp)
            example_data_setup.set(True)



    def _state_callback_setup():
        # We want to minize duplicate state handling, but also keep the states
        #  independent. We'll set up observers for changes here so that they
        #  automatically keep the states in sync.
        measurements = Ref(LOCAL_STATE.fields.measurements)
        total_galaxies = Ref(COMPONENT_STATE.fields.total_galaxies)
        measurements.subscribe_change(
            lambda *args: total_galaxies.set(len(measurements.value))
        )
        
        example_measurements = Ref(LOCAL_STATE.fields.example_measurements)
        def _on_example_measurement_change(meas):
            # make sure the 2nd one is initialized
            initialize_second_example_measurement()
            
            # make sure it is in glue
            add_or_update_example_measurements_to_glue()

            # make sure it is in the seed data
            _update_seed_data_with_examples(gjapp, meas)
            
        example_measurements.subscribe(
            _on_example_measurement_change
        )
        
        def _on_marker_updated(marker):
            if COMPONENT_STATE.value.current_step.value >= Marker.rem_vel1.value:
                initialize_second_example_measurement() # either set them to current or keep from DB
            if COMPONENT_STATE.value.current_step_between(Marker.mee_gui1, Marker.sel_gal4):
                selection_tool_bg_count.set(selection_tool_bg_count.value + 1)

        Ref(COMPONENT_STATE.fields.current_step).subscribe(_on_marker_updated)


    solara.use_memo(_state_callback_setup, dependencies=[])

    @computed
    def use_second_measurement():
        return Ref(COMPONENT_STATE.fields.current_step).value.value >= Marker.rem_vel1.value

    @computed
    def selected_example_measurement():
        return Ref(LOCAL_STATE.fields.get_example_measurement).value(
            Ref(COMPONENT_STATE.fields.selected_example_galaxy).value,
            measurement_number='second' if use_second_measurement.value else 'first')

    @computed
    def selected_measurement():
        return Ref(LOCAL_STATE.fields.get_measurement).value(Ref(COMPONENT_STATE.fields.selected_galaxy).value)
    

    def _init_glue_data_setup():
        logger.info("The glue data use effect")
        if Ref(LOCAL_STATE.fields.measurements_loaded).value:
            add_or_update_example_measurements_to_glue()
            initialize_second_example_measurement()

    solara.use_effect(_init_glue_data_setup, dependencies=[Ref(LOCAL_STATE.fields.measurements_loaded).value])
    selection_tool_bg_count = solara.use_reactive(0)

    def _fill_galaxies():
        fill_add_all_measurements(LOCAL_API, LOCAL_STATE, GLOBAL_STATE)

    def _fill_lambdas():
        fill_and_add_wavelengths(LOCAL_API, LOCAL_STATE, GLOBAL_STATE)

    def _fill_stage1_go_stage2():
        fill_and_add_velocities(LOCAL_API, LOCAL_STATE, GLOBAL_STATE)
        push_to_route(router, location, f"02-distance-introduction")

    def _select_random_galaxies():
        need = 5 - len(LOCAL_STATE.value.measurements)
        if need <= 0:
            return
        galaxies: list = LOCAL_API.get_galaxies(LOCAL_STATE)
        sample = np.random.choice(galaxies, size=need, replace=False)
        new_measurements = [StudentMeasurement(student_id=GLOBAL_STATE.value.student.id,
                                               galaxy=galaxy)
                             for galaxy in sample]
        measurements = LOCAL_STATE.value.measurements + new_measurements
        Ref(LOCAL_STATE.fields.measurements).set(measurements)
    
    def _select_one_random_galaxy():
        if len(LOCAL_STATE.value.measurements) >= 5:
            return
        need = 1
        galaxies = LOCAL_API.get_galaxies(LOCAL_STATE)
        rng = np.random.default_rng()
        index = rng.integers(low=0, high=len(galaxies)-1, size=need)[0]
        galaxy = galaxies[index]
        selection_tool_candidate_galaxy.set(galaxy.model_dump())

    def num_bad_velocities():
        measurements = Ref(LOCAL_STATE.fields.measurements)
        num = 0
        for meas in measurements.value:
            if meas.obs_wave_value is None or meas.rest_wave_value is None:
                # Skip measurements with missing data cuz they have not been attempted
                continue
            elif is_wavelength_poorly_measured(meas.obs_wave_value, meas.rest_wave_value, meas.galaxy.z):
                num += 1
        
        has_multiple_bad_velocities = Ref(COMPONENT_STATE.fields.has_multiple_bad_velocities)
        has_multiple_bad_velocities.set(num > 1)
        return num
    
    def set_obs_wave_total():
        obs_wave_total = Ref(COMPONENT_STATE.fields.obs_wave_total)
        measurements = LOCAL_STATE.value.measurements
        num = 0
        for meas in measurements:
            # print(meas)
            if meas.obs_wave_value is not None:
                num += 1
        obs_wave_total.set(num)

    def _initialize_state(isloaded):
        if (not isloaded):
            return

        if COMPONENT_STATE.value.current_step.value == Marker.sel_gal2.value:
            if COMPONENT_STATE.value.total_galaxies == 5:
                transition_to(COMPONENT_STATE, Marker.sel_gal3, force=True)

        if COMPONENT_STATE.value.current_step.value > Marker.cho_row1.value:
            COMPONENT_STATE.value.selected_example_galaxy = 1576  # id of the first example galaxy

    loaded_component_state.subscribe(_initialize_state)
    
    def print_selected_galaxy(galaxy):
        print('selected galaxy is now:', galaxy)

    

    def print_selected_example_galaxy(galaxy):
        print('selected example galaxy is now:', galaxy)

    sync_wavelength_line = solara.use_reactive(6565.0)
    sync_velocity_line = solara.use_reactive(0.0)
    spectrum_bounds = solara.use_reactive([])
    dotplot_bounds = solara.use_reactive([])

    @computed
    def show_synced_lines():
        if not example_data_setup.value:
            return False
        return Ref(COMPONENT_STATE.fields.current_step).value.value >= Marker.dot_seq5.value and Ref(COMPONENT_STATE.fields.dotplot_click_count).value > 0

    
    ## ----- Make sure we are initialized in the correct state ----- ##
    def sync_example_velocity_to_wavelength(velocity):
        if len(LOCAL_STATE.value.example_measurements) > 0:
            lambda_rest = LOCAL_STATE.value.example_measurements[0].rest_wave_value
            lambda_obs = v2w(velocity, lambda_rest)
            logger.debug(f'sync_example_velocity_to_wavelength {velocity:0.2f} -> {lambda_obs:0.2f}')
            return lambda_obs
    
    def sync_example_wavelength_to_velocity(wavelength):
        if len(LOCAL_STATE.value.example_measurements) > 0:
            lambda_rest = LOCAL_STATE.value.example_measurements[0].rest_wave_value
            velocity = w2v(wavelength, lambda_rest)
            logger.debug(f'sync_example_wavelength_to_velocity {wavelength:0.2f} -> {velocity:0.2f}')
            return velocity
    
    def sync_spectrum_to_dotplot_range(value):
        if len(LOCAL_STATE.value.example_measurements) > 0:
            logger.debug('Setting dotplot range from spectrum range')
            lambda_rest = LOCAL_STATE.value.example_measurements[0].rest_wave_value
            return [w2v(v, lambda_rest) for v in value]
    
    def sync_dotplot_to_spectrum_range(value):
        if len(LOCAL_STATE.value.example_measurements) > 0:
            logger.debug('Setting spectrum range from dotplot range')
            lambda_rest = LOCAL_STATE.value.example_measurements[0].rest_wave_value
            return [v2w(v, lambda_rest) for v in value]

    def _reactive_subscription_setup():
        Ref(COMPONENT_STATE.fields.selected_galaxy).subscribe(print_selected_galaxy)
        Ref(COMPONENT_STATE.fields.selected_example_galaxy).subscribe(print_selected_example_galaxy)

        
        sync_reactives(spectrum_bounds, 
                       dotplot_bounds, 
                       sync_spectrum_to_dotplot_range, 
                       sync_dotplot_to_spectrum_range)
        
    solara.use_effect(_reactive_subscription_setup, dependencies=[])

    
    def dotplot_click_callback(point):
            Ref(COMPONENT_STATE.fields.dotplot_click_count).set(COMPONENT_STATE.value.dotplot_click_count + 1)
            sync_velocity_line.set(point.xs[0])
            wavelength = sync_example_velocity_to_wavelength(point.xs[0])
            if wavelength:
                sync_wavelength_line.set(wavelength)
 
    speech = Ref(GLOBAL_STATE.fields.speech)




    if GLOBAL_STATE.value.show_team_interface:
        with rv.Row():
            with solara.Column():
                StateEditor(Marker, COMPONENT_STATE, LOCAL_STATE, LOCAL_API, show_all=not GLOBAL_STATE.value.educator)
            with solara.Column():
                solara.Button(label="Shortcut: Fill in galaxy velocity data & Jump to Stage 2", on_click=_fill_stage1_go_stage2, classes=["demo-button"])
                solara.Button(label="Choose 5 random galaxies", on_click=_select_random_galaxies, classes=["demo-button"])

    with rv.Row():
        with rv.Col(cols=12, lg=4):
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineIntro.vue",
                event_back_callback=lambda _: push_to_route(router, location, "/"),
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.mee_gui1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies1.vue",
                # If at least 1 galaxy has already been selected, we want to go straight from here to sel_gal3.
                event_next_callback=lambda _: transition_to(COMPONENT_STATE, Marker.sel_gal2 if COMPONENT_STATE.value.total_galaxies == 0 else Marker.sel_gal3, force=True),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sel_gal1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies2.vue",
                # I think we don't need this next callback because meeting the "next" criteria will autoadvance you to not_gal1 anyway, and then we skip over this guideline if we go backwards from sel_gal3. (But leave it just in case)
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sel_gal2),
                state_view={
                    "total_galaxies": COMPONENT_STATE.value.total_galaxies,
                    "galaxy_is_selected": COMPONENT_STATE.value.galaxy_is_selected,
                },
                speech=speech.value,
            )

            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies3.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                # You can't get to this marker until at least 1 galaxy has been selected. Once a galaxy has been selected, sel_gal2 doesn't make sense, so jump back to sel_gal1.
                event_back_callback=lambda _: transition_to(COMPONENT_STATE, Marker.sel_gal1, force=True),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sel_gal3),
                state_view={
                    "total_galaxies": COMPONENT_STATE.value.total_galaxies,
                    "galaxy_is_selected": COMPONENT_STATE.value.galaxy_is_selected,
                },
                speech=speech.value,
            )

            if COMPONENT_STATE.value.is_current_step(Marker.sel_gal2) or COMPONENT_STATE.value.is_current_step(Marker.sel_gal3):
                solara.Button(label="Select a random galaxy", on_click=_select_one_random_galaxy, classes=["emergency-button"])

            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineSelectGalaxies4.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sel_gal4),
                speech=speech.value,
            )

        with rv.Col(cols=12, lg=8):
            
            show_snackbar = Ref(LOCAL_STATE.fields.show_snackbar)
            async def snackbar_off(value = None):
                if show_snackbar.value:
                    await asyncio.sleep(3)
                    show_snackbar.set(False)
            solara.lab.use_task(snackbar_off, dependencies=[show_snackbar])
            
            def _galaxy_added_callback(galaxy_data: dict):
                galaxy = LOCAL_STATE.value.galaxies[int(galaxy_data['id'])]
                already_exists = galaxy.id in [
                    x.galaxy_id for x in LOCAL_STATE.value.measurements
                ]

                if already_exists:
                    return

                if len(LOCAL_STATE.value.measurements) == 5:
                    show_snackbar = Ref(LOCAL_STATE.fields.show_snackbar)
                    snackbar_message = Ref(LOCAL_STATE.fields.snackbar_message)

                    show_snackbar.set(True)
                    snackbar_message.set(
                        "You've already selected 5 galaxies. Continue forth!"
                    )
                    logger.info("Attempted to add more than 5 galaxies.")
                    return

                logger.info("Adding galaxy `%s` to measurements.", galaxy.id)

                measurements = Ref(LOCAL_STATE.fields.measurements)

                measurements.set(
                    measurements.value
                    + [
                        StudentMeasurement(
                            student_id=GLOBAL_STATE.value.student.id,
                            galaxy=galaxy,
                        )
                    ]
                )
                
                
            total_galaxies = Ref(COMPONENT_STATE.fields.total_galaxies)
            def advance_on_total_galaxies(value):
                if COMPONENT_STATE.value.current_step == Marker.sel_gal2:
                    if value == 1:
                        transition_to(COMPONENT_STATE, Marker.not_gal1)
            total_galaxies.subscribe(advance_on_total_galaxies)

            def _galaxy_selected_callback(galaxy_data: dict):
                galaxy = LOCAL_STATE.value.galaxies[int(galaxy_data['id'])]
                selected_galaxy = Ref(COMPONENT_STATE.fields.selected_galaxy)
                selected_galaxy.set(galaxy.id)
                galaxy_is_selected = Ref(COMPONENT_STATE.fields.galaxy_is_selected)
                galaxy_is_selected.set(True)  

            def _deselect_galaxy_callback():
                selected_galaxy = Ref(COMPONENT_STATE.fields.selected_galaxy)
                selected_galaxy.set(None)
                galaxy_is_selected = Ref(COMPONENT_STATE.fields.galaxy_is_selected)
                galaxy_is_selected.set(False)  

            show_example_data_table = COMPONENT_STATE.value.current_step_between(
                Marker.cho_row1, Marker.rem_vel1 
            )
            selection_tool_measurement = selected_example_measurement if show_example_data_table else selected_measurement
            selection_tool_galaxy = selection_tool_measurement.value.galaxy.model_dump() \
                                        if (selection_tool_measurement.value is not None and selection_tool_measurement.value.galaxy is not None) \
                                        else None

            def _on_wwt_ready_callback():
                Ref(COMPONENT_STATE.fields.wwt_ready).set(True)
            
            SelectionTool(
                show_galaxies=COMPONENT_STATE.value.current_step_in(
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
                solara.Info(label=LOCAL_STATE.value.snackbar_message)        

    # Measurement Table Row

    with rv.Row():
        with rv.Col(cols=12, lg=4):
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineNoticeGalaxyTable.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                # You can't get to this marker until at least 1 galaxy has been selected. Once a galaxy has been selected, sel_gal2 doesn't make sense, so jump back to sel_gal1.
                event_back_callback=lambda _: transition_to(COMPONENT_STATE, Marker.sel_gal1, force=True),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.not_gal1),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineChooseRow.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.cho_row1),
                speech=speech.value,
            )
            
            validation_4_failed = Ref(
                COMPONENT_STATE.fields.doppler_state.validation_4_failed
            )
            
            show_values = Ref(COMPONENT_STATE.fields.show_dop_cal4_values)
            
            def _on_validate_transition(validated):
                logger.debug("Validated transition to dop_cal5: %s", validated)
                validation_4_failed.set(not validated)
                show_values.set(validated)
                if not validated:
                    return
                
                if validated:
                    transition_to(COMPONENT_STATE, Marker.dop_cal5)

                show_doppler_dialog = Ref(COMPONENT_STATE.fields.show_doppler_dialog)
                logger.debug("Setting show_doppler_dialog to %s", validated)
                show_doppler_dialog.set(validated)

            
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDopplerCalc4.vue",
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.current_step_in(
                    [Marker.dop_cal4, Marker.dop_cal5]
                ),
                state_view={
                    "lambda_obs": round(COMPONENT_STATE.value.obs_wave),
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
            if COMPONENT_STATE.value.is_current_step(Marker.dop_cal5):
                show_doppler_dialog = Ref(COMPONENT_STATE.fields.show_doppler_dialog)
                step = Ref(COMPONENT_STATE.fields.doppler_state.step)
                validation_5_failed = Ref(
                    COMPONENT_STATE.fields.doppler_state.validation_5_failed
                )
                max_step_completed_5 = Ref(
                    COMPONENT_STATE.fields.doppler_state.max_step_completed_5
                )
                student_c = Ref(COMPONENT_STATE.fields.doppler_state.student_c)
                velocity_calculated = Ref(
                    COMPONENT_STATE.fields.doppler_state.velocity_calculated
                )

                def _velocity_calculated_callback(value):
                    example_measurement_index = (
                        LOCAL_STATE.value.get_example_measurement_index(
                            COMPONENT_STATE.value.selected_example_galaxy,
                            measurement_number='first'
                        )
                    )
                    if example_measurement_index is None:
                        return
                    example_measurement = Ref(
                        LOCAL_STATE.fields.example_measurements[
                            example_measurement_index
                        ]
                    )
                    example_measurement.set(
                        example_measurement.value.model_copy(
                            update={"velocity_value": round(value)}
                        )
                    )
                    

                DopplerSlideshow(
                    dialog=COMPONENT_STATE.value.show_doppler_dialog,
                    titles=COMPONENT_STATE.value.doppler_state.titles,
                    step=COMPONENT_STATE.value.doppler_state.step,
                    length=COMPONENT_STATE.value.doppler_state.length,
                    lambda_obs=round(COMPONENT_STATE.value.obs_wave),
                    lambda_rest=(
                        selected_example_measurement.value.rest_wave_value
                        if selected_example_measurement.value is not None
                        else None
                    ),
                    max_step_completed_5=COMPONENT_STATE.value.doppler_state.max_step_completed_5,
                    failed_validation_5=COMPONENT_STATE.value.doppler_state.validation_5_failed,
                    interact_steps_5=COMPONENT_STATE.value.doppler_state.interact_steps_5,
                    student_c=COMPONENT_STATE.value.doppler_state.student_c,
                    student_vel_calc=COMPONENT_STATE.value.doppler_state.velocity_calculated,
                    event_set_dialog=show_doppler_dialog.set,
                    event_set_step=step.set,
                    event_set_failed_validation_5=validation_5_failed.set,
                    event_set_max_step_completed_5=max_step_completed_5.set,
                    event_set_student_vel_calc=velocity_calculated.set,
                    event_set_student_vel=_velocity_calculated_callback,
                    event_set_student_c=student_c.set,
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                    state_view={
                        "mc_score": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "interpret-velocity"
                        ),
                        "score_tag": "interpret-velocity",
                    },
                    show_team_interface=GLOBAL_STATE.value.show_team_interface,
                )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineCheckMeasurement.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: _on_validate_transition(True), # Send user back to dop_cal5 and open dialog
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.che_mea1),
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
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.rem_gal1),
                state_view={
                    "obswaves_total": COMPONENT_STATE.value.obs_wave_total,
                    "has_bad_velocities": COMPONENT_STATE.value.has_bad_velocities,
                    "has_multiple_bad_velocities": COMPONENT_STATE.value.has_multiple_bad_velocities,
                    "selected_galaxy": (
                        selected_measurement.value.dict()
                        if selected_measurement.value is not None
                        else None
                    ),
                },
                speech=speech.value,
            )
            if GLOBAL_STATE.value.show_team_interface:
                if COMPONENT_STATE.value.is_current_step(Marker.rem_gal1):
                    solara.Button(label="DEMO SHORTCUT: FILL λ MEASUREMENTS", on_click=_fill_lambdas, style="text-transform: none;", classes=["demo-button"])
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineDopplerCalc6.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.dop_cal6),
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineReflectVelValues.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                show=COMPONENT_STATE.value.is_current_step(Marker.ref_vel1),
                state_view={'mc_score': get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "reflect_vel_value"), 'score_tag': 'reflect_vel_value'},
                speech=speech.value,
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineEndStage1.vue",
                event_next_callback=lambda _: push_to_route(router, location, "02-distance-introduction"),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.end_sta1),
                state_view={
                    "has_bad_velocities": COMPONENT_STATE.value.has_bad_velocities,
                    "has_multiple_bad_velocities": COMPONENT_STATE.value.has_multiple_bad_velocities,
                },
                speech=speech.value,
            )

        with rv.Col(cols=12, lg=8):
            show_example_data_table = COMPONENT_STATE.value.current_step_between(
                Marker.cho_row1, Marker.rem_vel1 
            )

            if show_example_data_table:
                selected_example_galaxy = Ref(
                    COMPONENT_STATE.fields.selected_example_galaxy
                )
                
                @computed
                def example_galaxy_data():
                    if use_second_measurement.value:
                        return [
                            x.dict() for x in LOCAL_STATE.value.example_measurements if x.measurement_number == 'second'
                        ]
                    else:
                        return [
                            x.dict() for x in LOCAL_STATE.value.example_measurements if x.measurement_number == 'first'
                        ]

                @computed
                def selected_example_galaxy_index():
                    index = LOCAL_STATE.value.get_example_measurement_index(
                        selected_example_galaxy.value,
                        measurement_number='second' if use_second_measurement.value else 'first')
                    if index is None:
                        return []
                    else:
                        return [0]

                def update_example_galaxy(galaxy):
                    flag = galaxy.get("value", True)
                    value = galaxy["item"]["galaxy_id"] if flag else None
                    selected_example_galaxy = Ref(COMPONENT_STATE.fields.selected_example_galaxy)
                    if value is not None:
                        galaxy = LOCAL_STATE.value.get_example_measurement(value, measurement_number='second' if use_second_measurement.value else 'first')
                        if galaxy is not None:
                            value = galaxy.galaxy_id
                        else:
                            value = None
                        
                    selected_example_galaxy.set(value)
                
                
                common_headers = [
                                    {"text": "Galaxy ID", "align": "start","sortable": False,"value": "name",},
                                    {"text": "Element", "value": "element"},
                                    {"text": "&lambda;<sub>rest</sub> (&Aring;)",
                                     "value": "rest_wave_value"},
                                    {"text": "&lambda;<sub>obs</sub> (&Aring;)",
                                     "value": "obs_wave_value"},
                                    {"text": "Velocity (km/s)", "value": "velocity_value"},
                                ]
                if use_second_measurement.value:
                    measnum_header = {"text": "Measurement", "value": "measurement_number"}
                    common_headers.append(measnum_header)

                
                # with solara.Card(title="Remove: for testing", style={'background-color': 'var(--warning-dark)'}):
                #     solara.Text(f"{COMPONENT_STATE.value.obs_wave}")
                #     DataTable(title="Example Measurements",
                #             items=[x.model_dump() for x in LOCAL_STATE.value.example_measurements])
                

                DataTable(
                    title="Example Galaxy",
                    headers=common_headers,
                    items=example_galaxy_data.value,
                    selected_indices=selected_example_galaxy_index.value,
                    show_select=COMPONENT_STATE.value.current_step_at_or_after(Marker.cho_row1),
                    event_on_row_selected=update_example_galaxy,
                )
            else:
                selected_galaxy = Ref(COMPONENT_STATE.fields.selected_galaxy)

                def _on_table_row_selected(row):
                    galaxy_measurement = LOCAL_STATE.value.get_measurement(
                        row["item"]["galaxy_id"]
                    )
                    if galaxy_measurement is not None:
                        selected_galaxy.set(galaxy_measurement.galaxy_id)

                    obs_wave = Ref(COMPONENT_STATE.fields.obs_wave)
                    obs_wave.set(0)

                def _on_calculate_velocity():
                    for i in range(len(LOCAL_STATE.value.measurements)):
                        measurement = Ref(LOCAL_STATE.fields.measurements[i])
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

                        velocities_total = Ref(COMPONENT_STATE.fields.velocities_total)
                        velocities_total.set(velocities_total.value + 1)

                @computed
                def selected_galaxy_index():
                    index = LOCAL_STATE.value.get_measurement_index(selected_galaxy.value)
                    if index is None:
                        return []
                    else:
                        return [index]

                DataTable(
                    title="My Galaxies",
                    items=[x.dict() for x in LOCAL_STATE.value.measurements],
                    selected_indices=selected_galaxy_index.value,
                    show_select=COMPONENT_STATE.value.current_step_at_or_after(
                        Marker.cho_row1
                    ),
                    button_icon="mdi-run-fast",
                    button_tooltip="Calculate & Fill Velocities",
                    show_button=COMPONENT_STATE.value.is_current_step(
                        Marker.dop_cal6
                    ),
                    event_on_row_selected=_on_table_row_selected,
                    event_on_button_pressed=lambda _: _on_calculate_velocity(),
                )

    # dot plot slideshow button row

    if COMPONENT_STATE.value.current_step_between(Marker.int_dot1, Marker.rem_vel1): 
        with rv.Row(class_="no-padding"):
            with rv.Col(cols=12, lg=4, class_="no-padding"):
                pass
            with rv.Col(cols=12, lg=8, class_="no-padding"):
                with rv.Col(cols=4, offset=4, class_="no-padding"):
                    dotplot_tutorial_finished = Ref(
                        COMPONENT_STATE.fields.dotplot_tutorial_finished
                    )
                    
                    tut_viewer_data = None
                    if EXAMPLE_GALAXY_SEED_DATA+'_tutorial' in gjapp.data_collection:
                        tut_viewer_data: Data = gjapp.data_collection[EXAMPLE_GALAXY_SEED_DATA+'_tutorial']
                    # solara.Markdown(tut_viewer_data.to_dataframe().to_markdown())
                    DotplotTutorialSlideshow(
                        dialog=COMPONENT_STATE.value.show_dotplot_tutorial_dialog,
                        step=COMPONENT_STATE.value.dotplot_tutorial_state.step,
                        length=COMPONENT_STATE.value.dotplot_tutorial_state.length,
                        max_step_completed=COMPONENT_STATE.value.dotplot_tutorial_state.max_step_completed,
                        dotplot_viewer=DotplotViewer(gjapp,
                                                    data=tut_viewer_data,
                                                    component_id=DB_VELOCITY_FIELD,
                                                    vertical_line_visible=False,
                                                    line_marker_color=LIGHT_GENERIC_COLOR,
                                                    unit="km / s",
                                                    x_label="Velocity (km/s)",
                                                    y_label="Count",
                                                    nbin=20
                                                    ),
                                                    
                        event_tutorial_finished=lambda _: dotplot_tutorial_finished.set(
                            True
                        ),
                        event_show_dialog=lambda v: Ref(
                            COMPONENT_STATE.fields.show_dotplot_tutorial_dialog
                        ).set(v),
                        event_set_step = Ref(COMPONENT_STATE.fields.dotplot_tutorial_state.step).set,
                        show_team_interface=GLOBAL_STATE.value.show_team_interface,
                    )
                
    # Dot Plot 1st measurement row
    if COMPONENT_STATE.value.current_step_between(Marker.int_dot1, Marker.rem_vel1): 
        with rv.Row(class_="no-y-padding"):
            with rv.Col(cols=12, lg=4, class_="no-y-padding"):
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineIntroDotplot.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.int_dot1),
                    speech=speech.value,
                    state_view={
                        "color": MY_DATA_COLOR_NAME
                    }
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence01.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq1),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence02.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq2),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence03.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq3),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence04a.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq4a),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence05.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq5),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence06.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq6),
                    speech=speech.value,
                    event_zoom_to_range= lambda event: dotplot_bounds.set([9000, 13500]),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence07.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq7),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence08.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                    event_zoom_to_range= lambda event: dotplot_bounds.set([9000, 13500]),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq8),
                    state_view={
                        "mc_score": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "vel_meas_consensus"),
                        "score_tag": "vel_meas_consensus",
                    },
                    speech=speech.value,
                )


            if COMPONENT_STATE.value.current_step_between(Marker.int_dot1, Marker.rem_vel1):
                with rv.Col(cols=12, lg=8, class_="no-y-padding"):
                                            
                    if (EXAMPLE_GALAXY_MEASUREMENTS in gjapp.data_collection 
                        and len(LOCAL_STATE.value.example_measurements) > 0
                        and example_data_setup.value
                        ):
                        viewer_data = [
                            gjapp.data_collection[EXAMPLE_GALAXY_SEED_DATA + '_first'],
                            gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS]
                        ]
                        
                        ignore = [gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS]]
                        if COMPONENT_STATE.value.current_step.value != Marker.rem_vel1.value:
                            ignore += [subset_by_label(gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS], "second measurement")]
                        else:
                            ignore += [subset_by_label(gjapp.data_collection[EXAMPLE_GALAXY_MEASUREMENTS], "first measurement")]
                        
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
                                    [3796.6455078125, 9187.5576171875])),
                            hide_layers=ignore,  # type: ignore
                        )

    # Spectrum Viewer row
    if COMPONENT_STATE.value.current_step_between(Marker.mee_spe1, Marker.che_mea1) or COMPONENT_STATE.value.current_step_between(Marker.dot_seq4, Marker.rem_vel1) or COMPONENT_STATE.value.current_step_at_or_after(Marker.rem_gal1):
        with rv.Row():
            with rv.Col(cols=12, lg=4):
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineSpectrum.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.mee_spe1),
                    state_view={
                        "spectrum_tutorial_opened": COMPONENT_STATE.value.spectrum_tutorial_opened
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
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.res_wav1),
                    state_view={
                        "selected_example_galaxy": selected_example_galaxy_data,
                        "lambda_on": COMPONENT_STATE.value.rest_wave_tool_activated,
                    },
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineObswave1.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.obs_wav1),
                    state_view={"selected_example_galaxy": selected_example_galaxy_data},
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineObswave2.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.obs_wav2),
                    state_view={
                        "selected_example_galaxy": selected_example_galaxy_data,
                        "zoom_tool_activated": COMPONENT_STATE.value.zoom_tool_activated,
                        "zoom_tool_active": COMPONENT_STATE.value.zoom_tool_active,
                    },
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDopplerCalc0.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dop_cal0),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDopplerCalc2.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dop_cal2),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence04.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq4),
                    speech=speech.value,
                    state_view={
                        "color": MY_DATA_COLOR_NAME,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence10.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq10),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineDotSequence11.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.dot_seq11),
                    speech=speech.value,
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineRemeasureVelocity.vue",
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.rem_vel1),
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
                    event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                    event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                    can_advance=COMPONENT_STATE.value.can_transition(next=True),
                    show=COMPONENT_STATE.value.is_current_step(Marker.ref_dat1),
                    speech=speech.value,
                )

            with rv.Col(cols=12, lg=8):
                show_example_spectrum = COMPONENT_STATE.value.current_step_between(
                    Marker.mee_spe1, Marker.che_mea1
                ) or COMPONENT_STATE.value.current_step_between(
                    Marker.dot_seq4, Marker.rem_vel1 
                )

                show_galaxy_spectrum = COMPONENT_STATE.value.current_step_at_or_after(
                    Marker.rem_gal1
                )

                if show_example_spectrum:
                    def _example_wavelength_measured_callback(value):
                        example_measurement_index = (
                            LOCAL_STATE.value.get_example_measurement_index(
                                COMPONENT_STATE.value.selected_example_galaxy,
                                measurement_number='second' if use_second_measurement.value else 'first'
                            )
                        )
                        if example_measurement_index is None:
                            return
                        
                        example_measurements = LOCAL_STATE.value.example_measurements
                        example_measurement = Ref(
                            LOCAL_STATE.fields.example_measurements[
                                example_measurement_index
                            ]
                        )

                        obs_wave = Ref(COMPONENT_STATE.fields.obs_wave)
                        obs_wave.set(value)
                        
                        if example_measurement.value.velocity_value is None:
                            example_measurement.set(
                                example_measurement.value.model_copy(
                                    update={"obs_wave_value": round(value)}
                                )
                            )
                        else:
                            velocity = velocity_from_wavelengths(value, example_measurement.value.rest_wave_value)
                            example_measurement.set(
                                example_measurement.value.model_copy(
                                    update={"obs_wave_value": round(value), "velocity_value": velocity}
                                )
                            )
                        # example_measurements[example_measurement_index] = example_measurement.value
                        # Ref(LOCAL_STATE.fields.example_measurements).set(example_measurements)
                        obs_wave_tool_used.set(True)
                        # obs_wave = Ref(COMPONENT_STATE.fields.obs_wave)
                        # obs_wave.set(value)
                        
                    def _on_set_marker_location(value):
                        logger.debug('Setting marker location spectrum -> dotplot')
                        velocity = sync_example_wavelength_to_velocity(value)
                        if velocity:
                            logger.debug(f'Setting velocity {velocity: 0.2f} ')
                            sync_velocity_line.set(velocity)

                    obs_wave_tool_used = Ref(COMPONENT_STATE.fields.obs_wave_tool_used)
                    rest_wave_tool_activated = Ref(
                        COMPONENT_STATE.fields.rest_wave_tool_activated
                    )
                    zoom_tool_activated = Ref(
                        COMPONENT_STATE.fields.zoom_tool_activated
                    )
                    zoom_tool_active = Ref(
                        COMPONENT_STATE.fields.zoom_tool_active
                    )
                    
                    @computed
                    def obs_wav_marker_value():
                        meas = LOCAL_STATE.value.example_measurements
                        if LOCAL_STATE.value.measurements_loaded and len(meas) > 0:
                            step = COMPONENT_STATE.value.current_step.value
                            if step >= Marker.rem_vel1.value and meas[1].obs_wave_value is not None:
                                return meas[1].obs_wave_value
                            elif step >= Marker.dot_seq1.value and meas[0].velocity_value is not None:
                                return meas[0].obs_wave_value
                        return COMPONENT_STATE.value.obs_wave


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
                        obs_wave=obs_wav_marker_value.value, #COMPONENT_STATE.value.obs_wave if COMPONENT_STATE.value.current_step < Marker.dot_seq1 else E,
                        spectrum_click_enabled=(
                            COMPONENT_STATE.value.current_step_between(
                            Marker.obs_wav1, Marker.obs_wav2
                        )
                        or COMPONENT_STATE.value.current_step.value == Marker.rem_vel1.value
                        ),
                        on_obs_wave_measured=_example_wavelength_measured_callback,
                        on_rest_wave_tool_clicked=lambda: rest_wave_tool_activated.set(
                            True
                        ),
                        on_zoom=_on_zoom,
                        on_reset_tool_clicked=_on_reset,
                        marker_position=sync_wavelength_line if show_synced_lines.value else None,
                        spectrum_bounds = spectrum_bounds, # type: ignore
                        show_obs_wave_line=COMPONENT_STATE.value.current_step_at_or_after(Marker.dot_seq4),
                        on_set_marker_position=_on_set_marker_location,
                    )

                elif show_galaxy_spectrum:
                    def _wavelength_measured_callback(value):
                        measurement_index = LOCAL_STATE.value.get_measurement_index(
                            COMPONENT_STATE.value.selected_galaxy
                        )
                        if measurement_index is None:
                            return

                        has_bad_velocities = Ref(
                            COMPONENT_STATE.fields.has_bad_velocities
                        )
                        is_bad = is_wavelength_poorly_measured(
                            value,
                            selected_measurement.value.rest_wave_value,
                            selected_measurement.value.galaxy.z,
                        )
                        has_bad_velocities.set(is_bad)
                        num_bad_velocities()

                        if not is_bad:

                            obs_wave = Ref(COMPONENT_STATE.fields.obs_wave)
                            obs_wave.set(value)

                            measurement = Ref(
                                LOCAL_STATE.fields.measurements[measurement_index]
                            )
                            
                            if measurement.value.velocity_value is None:
                                measurement.set(
                                    measurement.value.model_copy(
                                        update={"obs_wave_value": round(value)}
                                    )
                                )
                                
                            else:
                                velocity = velocity_from_wavelengths(value, measurement.value.rest_wave_value)
                                measurement.set(
                                    measurement.value.model_copy(
                                        update={"obs_wave_value": round(value), "velocity_value": velocity}
                                    )
                                )
                            
                            set_obs_wave_total()
                            
                            
                        else:
                            logger.info('Wavelength measurement is bad')

                    if COMPONENT_STATE.value.has_bad_velocities:
                        rv.Alert(
                            elevation=2,
                            icon="mdi-alert-circle-outline",
                            prominent=True,
                            dark=True,
                            class_="ma-2 student-warning",
                            children=["Your measured wavelength value is not within the expected range. Please try again. Ask your instructor if you are not sure where to measure."]
                        )

                    SpectrumViewer(
                        galaxy_data=(
                            selected_measurement.value.galaxy
                            if selected_measurement.value is not None
                            else None
                        ),
                        obs_wave=COMPONENT_STATE.value.obs_wave,
                        spectrum_click_enabled=COMPONENT_STATE.value.current_step_at_or_after(
                            Marker.obs_wav1
                        ),
                        on_obs_wave_measured=_wavelength_measured_callback,
                    )
                if COMPONENT_STATE.value.current_step_between(Marker.mee_spe1, Marker.rem_gal1): # center single button
                    with rv.Row():
                        with rv.Col(cols=4, offset=4):
                            spectrum_tutorial_opened = Ref(
                                COMPONENT_STATE.fields.spectrum_tutorial_opened
                            )
                            SpectrumSlideshow(
                                event_dialog_opened_callback=lambda _: spectrum_tutorial_opened.set(
                                    True
                                ),
                                image_location=get_image_path(router, "stage_one_spectrum"),
                                show_team_interface=GLOBAL_STATE.value.show_team_interface,
                            )
                
                if COMPONENT_STATE.value.current_step_at_or_after(Marker.ref_dat1): # space 2 buttons nicely
                    with rv.Row():
                        with rv.Col(cols=4, offset=2):
                            SpectrumSlideshow(
                                image_location=get_image_path(router, "stage_one_spectrum"),
                                show_team_interface=GLOBAL_STATE.value.show_team_interface,
                            )
                        with rv.Col(cols=4):
                            show_reflection_dialog = Ref(
                                COMPONENT_STATE.fields.show_reflection_dialog
                            )
                            reflect_step = Ref(
                                COMPONENT_STATE.fields.velocity_reflection_state.step
                            )
                            reflect_max_step_completed = Ref(
                                COMPONENT_STATE.fields.velocity_reflection_state.max_step_completed
                            )
                            reflection_complete = Ref(COMPONENT_STATE.fields.reflection_complete)

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
                                dialog=COMPONENT_STATE.value.show_reflection_dialog,
                                step=COMPONENT_STATE.value.velocity_reflection_state.step,
                                max_step_completed=COMPONENT_STATE.value.velocity_reflection_state.max_step_completed,
                                reflection_complete=COMPONENT_STATE.value.reflection_complete,
                                state_view={
                                    "mc_score_2": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "wavelength-comparison"),
                                    "score_tag_2": "wavelength-comparison",
                                    "mc_score_3": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "galaxy-motion"),
                                    "score_tag_3": "galaxy-motion",
                                    "mc_score_4": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "steady-state-consistent"),
                                    "score_tag_4": "steady-state-consistent",
                                    "mc_score_5": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "moving-randomly-consistent"),
                                    "score_tag_5": "moving-randomly-consistent",
                                    "mc_score_6": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "peers-data-agree"),
                                    "score_tag_6": "peers-data-agree",
                                },
                                event_set_dialog=show_reflection_dialog.set,
                                event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                                # These are numbered based on window-item value
                                event_set_step=reflect_step.set,
                                event_set_max_step_completed=reflect_max_step_completed.set,
                                event_on_reflection_complete=lambda _: reflection_complete.set(
                                    True
                                ),
                                show_team_interface=GLOBAL_STATE.value.show_team_interface,
                            )
