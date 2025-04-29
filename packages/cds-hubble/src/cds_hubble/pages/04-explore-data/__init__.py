import asyncio
from cds_core.utils import empty_data_from_model_class, DEFAULT_VIEWER_HEIGHT
from cds_core.viewers import CDSScatterView
from echo import delay_callback
from glue.core import Data
from glue_jupyter import JupyterApplication
from ...base_component_state import transition_next, transition_previous
import numpy as np
from pathlib import Path
import reacton.ipyvuetify as rv
import solara
from solara.toestand import Ref
from typing import Dict, List, Tuple

from cds_core.components import ScaffoldAlert, StateEditor, ViewerLayout
from ...viewer_marker_colors import MY_DATA_COLOR, MY_CLASS_COLOR, GENERIC_COLOR
from ...components import DataTable, HubbleExpUniverseSlideshow, LineDrawViewer, PlotlyLayerToggle, Stage4WaitingScreen
from ...state import LOCAL_STATE, GLOBAL_STATE, StudentMeasurement, get_multiple_choice, get_free_response, mc_callback, fr_callback
from ...viewers.hubble_scatter_viewer import HubbleScatterView
from .component_state import COMPONENT_STATE, Marker
from ...remote import LOCAL_API
from ...utils import AGE_CONSTANT, models_to_glue_data, PLOTLY_MARGINS, get_image_path, push_to_route

from cds_core.logger import setup_logger
from cds_hubble.measurement_helpers import fill_add_all_measurements

logger = setup_logger("STAGE 4")

GUIDELINE_ROOT = Path(__file__).parent / "guidelines"

@solara.component
def Page():
    solara.Title("HubbleDS")
    loaded_component_state = solara.use_reactive(False)
    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    completed_count = solara.use_reactive(0)

    class_plot_data = solara.use_reactive([])

    # Are the buttons available to press?
    draw_active = solara.use_reactive(False)

    # Are the plotly traces actively displayed?
    clear_class_layer = solara.use_reactive(0)
    clear_drawn_line = solara.use_reactive(0)
    clear_fit_line = solara.use_reactive(0)

    skip_waiting_room, set_skip_waiting_room = solara.use_state(False)

    def glue_setup() -> Tuple[JupyterApplication, Dict[str, CDSScatterView]]:
        gjapp = JupyterApplication(
            GLOBAL_STATE.value.glue_data_collection, GLOBAL_STATE.value.glue_session
        )

        race_viewer = gjapp.new_data_viewer(HubbleScatterView, show=False)
        race_data = Data(**{
            "label": "Hubble Race Data",
            "Distance (km)": [12, 24, 30],
            "Velocity (km/hr)": [4, 8, 10],
        })
        race_data = GLOBAL_STATE.value.add_or_update_data(race_data)
        race_data.style.color = GENERIC_COLOR
        race_data.style.alpha = 1
        race_data.style.markersize = 10
        race_viewer.add_data(race_data)
        race_viewer.state.x_att = race_data.id["Distance (km)"]
        race_viewer.state.y_att = race_data.id["Velocity (km/hr)"]
        race_viewer.state.x_max = 1.1 * race_viewer.state.x_max
        race_viewer.state.y_max = 1.1 * race_viewer.state.y_max
        race_viewer.state.x_min = 0
        race_viewer.state.y_min = 0
        race_viewer.state.title = "Race Data"

        layer_viewer = gjapp.new_data_viewer(HubbleScatterView, show=False)
        layer_viewer.state.title = "Our Class Data"

        viewers = {
            "race": race_viewer,
            "layer": layer_viewer,
        }

        return gjapp, viewers

    gjapp, viewers = solara.use_memo(glue_setup, dependencies=[])

    def check_completed_students_count():
        logger.info("Checking how many students have completed measurements")
        count = LOCAL_API.get_students_completed_measurements_count(GLOBAL_STATE, LOCAL_STATE)
        logger.info(f"Count: {count}")
        return count

    def load_class_data():
        logger.info("Loading class data")
        class_measurements = LOCAL_API.get_class_measurements(GLOBAL_STATE, LOCAL_STATE)
        measurements = Ref(LOCAL_STATE.fields.class_measurements)
        student_ids = Ref(LOCAL_STATE.fields.stage_4_class_data_students)
        if not class_measurements:
            return []

        if student_ids.value:
            class_data_points = [m for m in class_measurements if m.student_id in student_ids.value]
        else:
            class_data_points = class_measurements
            ids = [int(id) for id in np.unique([m.student_id for m in class_measurements])]
            student_ids.set(ids)
        measurements.set(class_measurements)

        _on_class_data_loaded(class_data_points)
        return class_data_points

    def _on_class_data_loaded(class_data_points: List[StudentMeasurement]):
        logger.info("Setting up class glue data")
        if not class_data_points:
            return

        class_data = models_to_glue_data(class_data_points, label="Stage 4 Class Data")
        if not class_data.components:
            class_data = empty_data_from_model_class(StudentMeasurement, label="Stage 4 Class Data")
        class_data = GLOBAL_STATE.value.add_or_update_data(class_data)
        class_data.style.color = MY_CLASS_COLOR
        class_data.style.alpha = 1
        class_data.style.markersize = 10

        layer_viewer = viewers["layer"]
        layer_viewer.add_data(class_data)
        layer_viewer.state.x_att = class_data.id['est_dist_value']
        layer_viewer.state.y_att = class_data.id['velocity_value']
        with delay_callback(layer_viewer.state, 'x_max', 'y_max'):
            layer_viewer.state.reset_limits()
            layer_viewer.state.x_max = 1.06 * layer_viewer.state.x_max
            layer_viewer.state.y_max = 1.06 * layer_viewer.state.y_max   
        layer_viewer.state.x_axislabel = "Distance (Mpc)"
        layer_viewer.state.y_axislabel = "Velocity (km/s)"
        layer_viewer.state.title = "Our Data"

        class_plot_data.set(class_data_points)

    async def keep_checking_class_data():
        enough_students_ready = Ref(LOCAL_STATE.fields.enough_students_ready)
        # Add a state guard in case task cancellation fails
        while COMPONENT_STATE.value.current_step == Marker.wwt_wait:
            count = check_completed_students_count()
            if (not enough_students_ready.value) and count >= 12:
                enough_students_ready.set(True)
            completed_count.set(count)
            await asyncio.sleep(10)

    class_ready_task = solara.lab.use_task(keep_checking_class_data, dependencies=[])

    def _on_waiting_room_advance():
        if class_ready_task.pending:
            try:
                class_ready_task.cancel()
            except RuntimeError:
                pass
        load_class_data()
        transition_next(COMPONENT_STATE)

    def _load_component_state():
        # Load stored component state from database, measurement data is
        # considered higher-level and is loaded when the story starts
        LOCAL_API.get_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)

        # TODO: What else to we need to do here?
        logger.info("Finished loading component state for stage 4.")

        value = LOCAL_STATE.value.enough_students_ready \
                or \
                (check_completed_students_count() >= 12)

        Ref(LOCAL_STATE.fields.enough_students_ready).set(value)
        if GLOBAL_STATE.value.educator:
            value = False
        set_skip_waiting_room(value)
        if value:
            if COMPONENT_STATE.value.current_step == Marker.wwt_wait:
                _on_waiting_room_advance()
            else:
                load_class_data()

        loaded_component_state.set(True)

    solara.use_memo(_load_component_state, dependencies=[])

    def _write_component_state():
        if not loaded_component_state.value:
            return

        # Listen for changes in the states and write them to the database
        res = LOCAL_API.put_stage_state(GLOBAL_STATE, LOCAL_STATE, COMPONENT_STATE)
        if res:
            logger.info("Wrote component state for stage 4 to database.")
        else:
            logger.info("Did not write component state for stage 4 to database.")


    solara.lab.use_task(_write_component_state, dependencies=[COMPONENT_STATE.value])

    student_plot_data = solara.use_reactive(LOCAL_STATE.value.measurements)
    async def _load_student_data():
        if not LOCAL_STATE.value.measurements_loaded:
            logger.info("Loading measurements")
            measurements = LOCAL_API.get_measurements(GLOBAL_STATE, LOCAL_STATE)
            student_plot_data.set(measurements)
    solara.lab.use_task(_load_student_data)

    # TODO: not sure what this is supposed to do
    if not (class_ready_task.finished or class_ready_task.pending):
        load_class_data()

    def _jump_stage_5():
        push_to_route(router, location, "05-class-results-uncertainty")

    current_step = Ref(COMPONENT_STATE.fields.current_step)

    @solara.lab.computed
    def draw_enabled():
        return current_step.value >= Marker.tre_lin2

    @solara.lab.computed
    def fit_enabled():
        return current_step.value >= Marker.bes_fit1

    @solara.lab.computed
    def display_best_fit_gal():
        return current_step.value >= Marker.hyp_gal1

    @solara.lab.computed
    def layers_enabled():
        return (current_step.value.is_between(Marker.tre_dat2, Marker.hub_exp1), True)

    best_fit_slope = Ref(LOCAL_STATE.fields.best_fit_slope)
    @solara.lab.computed
    def line_label():
        if current_step.value >= Marker.age_uni4 and best_fit_slope.value is not None:
            return f"Age: {round(AGE_CONSTANT / best_fit_slope.value)} Gyr"
        else:
            return None

    if GLOBAL_STATE.value.show_team_interface:
        with solara.Row():
            with solara.Column():
                StateEditor(Marker, COMPONENT_STATE, LOCAL_STATE, LOCAL_API, show_all=not GLOBAL_STATE.value.educator)
            with solara.Column():
                solara.Button(label="Shortcut: Jump to Stage 5", on_click=_jump_stage_5, classes=["demo-button"])

    if COMPONENT_STATE.value.current_step == Marker.wwt_wait:
        if not skip_waiting_room:
            Stage4WaitingScreen(
                completed_count=completed_count.value,
                can_advance=LOCAL_STATE.value.enough_students_ready,
                on_advance_click=_on_waiting_room_advance,
            )
            return
    else:
        try:
            if class_ready_task.pending:
                class_ready_task.cancel()
        except RuntimeError:
            pass

    def _state_callback_setup():
        def _on_marker_update(marker):
            if marker is Marker.tre_lin1:
                # What we really want is for the viewer to check if this layer is visible when it gets to this marker, and if so, clear it.
                clear_class_layer.set(clear_class_layer.value + 1)

            # This has the same issues as above.
            if marker is Marker.age_uni1:
                clear_drawn_line.set(clear_drawn_line.value + 1)
                draw_active.set(False)

        current_step.subscribe(_on_marker_update)

    solara.use_memo(_state_callback_setup, dependencies=[])

    if (len(LOCAL_STATE.value.measurements) == 0
        or not all(m.completed for m in LOCAL_STATE.value.measurements) # all([]) = True :/
        ):
        solara.Error(
            "You have not added any or have incomplete measurements. Please add/finish some before continuing.",
            icon="mdi-alert",
        )
        if GLOBAL_STATE.value.show_team_interface:
            def _fill_all_data():
                fill_add_all_measurements(LOCAL_API, LOCAL_STATE, GLOBAL_STATE)
            solara.Button(label="Shortcut: Fill in galaxy velocity data & Jump to Stage 2", on_click=_fill_all_data, classes=["demo-button"])
            _fill_all_data()
            best_fit_slope.set(16.9653)
        return

    with solara.ColumnsResponsive(12, large=[4,8]):
        with rv.Col():
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineExploreData.vue",
                event_back_callback=lambda _: push_to_route(router, location, "03-distance-measurements"),
                event_next_callback = lambda _: transition_next(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.exp_dat1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAgeUniverseEstimate3.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.age_uni3),
                state_view={
                    "age_const": AGE_CONSTANT,
                    "hypgal_distance": COMPONENT_STATE.value.best_fit_gal_dist,
                    "hypgal_velocity": COMPONENT_STATE.value.best_fit_gal_vel,
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAgeUniverseEstimate4.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.age_uni4),
                state_view={
                    "age_const": AGE_CONSTANT,
                    "hypgal_distance": COMPONENT_STATE.value.best_fit_gal_dist,
                    "hypgal_velocity": COMPONENT_STATE.value.best_fit_gal_vel,
                }
            )

        with rv.Col():
            DataTable(
                title="My Galaxies",
                items=[x.model_dump() for x in LOCAL_STATE.value.measurements],
                headers=[
                    {
                        "text": "Galaxy ID",
                        "align": "start",
                        "sortable": False,
                        "value": "galaxy.name"
                    },
                    { "text": "Velocity (km/s)", "value": "velocity_value" },
                    { "text": "Distance (Mpc)", "value": "est_dist_value" },
                ]
            )

    with solara.ColumnsResponsive(12, large=[4,8]):
        with rv.Col():
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineTrendsDataMC1.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.tre_dat1),
                event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                state_view={
                    "mc_score": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "tre-dat-mc1"),
                    "score_tag": "tre-dat-mc1"
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineTrendsData2.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.tre_dat2),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineTrendsDataMC3.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.tre_dat3),
                event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                state_view={
                    'mc_score': get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, 'tre-dat-mc3'),
                    'score_tag': 'tre-dat-mc3'
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineRelationshipVelDistMC.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.rel_vel1),
                event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                state_view={
                    'mc_score': get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, 'galaxy-trend'),
                    'score_tag': 'galaxy-trend'
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineTrendLines1.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.tre_lin1),               
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineTrendLinesDraw2.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.tre_lin2),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineBestFitLine.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.bes_fit1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineHubblesExpandingUniverse1.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.hub_exp1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAgeUniverse.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.age_uni1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineHypotheticalGalaxy.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.hyp_gal1),
                state_view={
                    "hypgal_distance": COMPONENT_STATE.value.best_fit_gal_dist,
                    "hypgal_velocity": COMPONENT_STATE.value.best_fit_gal_vel,
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAgeRaceEquation.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.age_rac1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineAgeUniverseEquation2.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.age_uni2),
                state_view={
                    "age_const": AGE_CONSTANT
                },             
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineYourAgeEstimate.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.you_age1),
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineShortcomingsEstReflect1.vue",
                event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sho_est1),
                event_fr_callback = lambda event: fr_callback(event, LOCAL_STATE, COMPONENT_STATE, lambda: LOCAL_API.put_story_state(GLOBAL_STATE, LOCAL_STATE)),
                state_view={
                    'free_response_a': get_free_response(LOCAL_STATE, COMPONENT_STATE,'shortcoming-1'),
                    'free_response_b': get_free_response(LOCAL_STATE, COMPONENT_STATE,'shortcoming-2'),
                    'free_response_c': get_free_response(LOCAL_STATE, COMPONENT_STATE,'other-shortcomings'),
                }
            )
            ScaffoldAlert(
                GUIDELINE_ROOT / "GuidelineShortcomingsEst2.vue",
                event_next_callback=lambda _: push_to_route(router, location, "05-class-results-uncertainty"),
                event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                can_advance=COMPONENT_STATE.value.can_transition(next=True),
                show=COMPONENT_STATE.value.is_current_step(Marker.sho_est2),
            )


        with rv.Col(class_="no-padding"):
            if COMPONENT_STATE.value.current_step_between(Marker.tre_dat1, Marker.sho_est2):
                with solara.Columns([3,9], classes=["no-padding"]):
                    colors = (MY_CLASS_COLOR, MY_DATA_COLOR)
                    sizes = (8, 12)
                    with rv.Col(class_="no-padding"):

                        def _layer_toggled(data):
                            if data["visible"] and data["index"] == 3:
                                Ref(COMPONENT_STATE.fields.class_data_displayed).set(True)

                        PlotlyLayerToggle(chart_id="line-draw-viewer",
                                          # (Plotly calls layers traces, but we'll use layers for consistency with glue).
                                          # For the line draw viewer:
                                          # Layer 0 = line that the student draws
                                          # Layer 1, 2 = fit lines for data layers.
                                          # Layer 3, 4 = data layers.
                                          # Layer 5 = endpoint for drawn line.
                                          # Add Layer 6 = best fit galaxy marker.
                                          layer_indices=(3, 4),

                                          # These are the indices (within the specified tuple, which has 2 data layers) of the layers that we want to have initially checked/displayed. 
                                          # If only 1 layer is selected, you still need the comma, otherwise this will be interpreted as an int instead of a tuple. This means "check & display layer 1, which is the student data layer."
                                          initial_selected=(1,),
                                          enabled=layers_enabled.value,
                                          colors=colors,
                                          labels=("Class Data", "My Data"),
                                          event_layer_toggled=_layer_toggled)
                    with rv.Col(class_="no-padding"):
                        if student_plot_data.value and class_plot_data.value:
                            # Note the ordering here - we want the student data on top
                            layers = (class_plot_data.value, student_plot_data.value)
                            layers_visible = (False, True)

                            plot_data=[
                                {
                                    "x": [t.est_dist_value for t in data],
                                    "y": [t.velocity_value for t in data],
                                    "mode": "markers",
                                    "marker": { "color": color, "size": size },
                                    "visible": visibility,    
                                    "hoverinfo": "none",
                                    "showlegend": False,
                                } for data, color, size, visibility in zip(layers, colors, sizes, layers_visible)
                            ]

                            draw_click_count = Ref(COMPONENT_STATE.fields.draw_click_count)
                            best_fit_click_count = Ref(COMPONENT_STATE.fields.best_fit_click_count)
                            best_fit_slope = Ref(LOCAL_STATE.fields.best_fit_slope)
                            best_fit_gal_vel = Ref(COMPONENT_STATE.fields.best_fit_gal_vel)
                            best_fit_gal_dist = Ref(COMPONENT_STATE.fields.best_fit_gal_dist)

                            def draw_click_cb():
                                draw_click_count.set(draw_click_count.value + 1)    

                            def best_fit_click_cb():
                                best_fit_click_count.set(best_fit_click_count.value + 1)

                            def line_fit_cb(args: Dict):
                                # student line is the 2nd of the 2 layers, so index=1
                                best_fit_slope.set(args["slopes"][1]) 
                                range = args["range"]
                                best_fit_gal_dist.set(round(range/2))
                                best_fit_gal_vel.set(round(best_fit_slope.value * best_fit_gal_dist.value))

                            LineDrawViewer(chart_id="line-draw-viewer",
                                           title="Our Data",
                                           plot_data=plot_data,
                                           on_draw_clicked=draw_click_cb,
                                           on_best_fit_clicked = best_fit_click_cb,
                                           on_line_fit=line_fit_cb,
                                           x_axis_label="Distance (Mpc)",
                                           y_axis_label="Velocity (km/s)",
                                           viewer_height=DEFAULT_VIEWER_HEIGHT,
                                           plot_margins=PLOTLY_MARGINS,
                                           draw_enabled=draw_enabled.value,
                                           fit_enabled=fit_enabled.value,
                                           line_label=line_label.value,
                                           display_best_fit_gal=display_best_fit_gal.value,
                                           draw_active=draw_active,
                                           # Use student data for best fit galaxy
                                           best_fit_gal_layer_index=1,
                                           clear_class_layer=clear_class_layer.value,
                                           clear_drawn_line=clear_drawn_line.value,
                                           clear_fit_line=clear_fit_line.value,)

            with rv.Col(cols=10, offset=1):
                if COMPONENT_STATE.value.current_step_at_or_after(
                Marker.hub_exp1):
                    dialog = Ref(COMPONENT_STATE.fields.show_hubble_slideshow_dialog)
                    step = Ref(COMPONENT_STATE.fields.hubble_slideshow_state.step)
                    max_step_completed = Ref(COMPONENT_STATE.fields.hubble_slideshow_state.max_step_completed)
                    slideshow_finished = Ref(COMPONENT_STATE.fields.hubble_slideshow_finished)

                    HubbleExpUniverseSlideshow(
                        race_viewer=ViewerLayout(viewer=viewers["race"]),
                        layer_viewer=ViewerLayout(viewers["layer"]),

                        dialog=COMPONENT_STATE.value.show_hubble_slideshow_dialog,
                        step=COMPONENT_STATE.value.hubble_slideshow_state.step,
                        max_step_completed=COMPONENT_STATE.value.hubble_slideshow_state.max_step_completed,
                        state_view={
                            "mc_score": get_multiple_choice(LOCAL_STATE, COMPONENT_STATE, "race-age"),
                            "score_tag": "race-age"
                        },
                        image_location=get_image_path(router,"stage_three"),
                        event_set_dialog=dialog.set,
                        event_set_step=step.set,
                        event_set_max_step_completed=max_step_completed.set,
                        event_mc_callback=lambda event: mc_callback(event, LOCAL_STATE, COMPONENT_STATE),
                        event_on_slideshow_finished=lambda _: slideshow_finished.set(True),
                        show_team_interface=GLOBAL_STATE.value.show_team_interface,
                    )
