from contextlib import ExitStack
from functools import partial
from pathlib import Path
from typing import Dict, Iterable, Optional, Tuple, cast

import numpy as np
import reacton.ipyvuetify as rv
import solara
from echo import delay_callback, add_callback
from glue.core.message import NumericalDataChangedMessage
from glue.core.subset import RangeSubsetState
from glue_jupyter import JupyterApplication
from glue_jupyter.link import link
from glue_plotly.viewers.common.viewer import PlotlyBaseView
from solara import Reactive
from solara.toestand import Ref

from cds_core.base_states import (
    transition_next,
    transition_previous,
    MultipleChoiceResponse,
    FreeResponse,
)
from cds_core.components import (
    LayerToggle,
    PercentageSelector,
    ScaffoldAlert,
    StateEditor,
    StatisticsSelector,
    ViewerLayout,
)
from cds_core.logger import setup_logger
from cds_core.app_state import AppState
from cds_core.utils import (
    empty_data_from_model_class,
    show_legend,
    show_layer_traces_in_legend,
)
from cds_core.viewers import CDSHistogramView
from .stage_state import Marker, StageState
from ...components import UncertaintySlideshow, IdSlider
from ...helpers.demo_helpers import set_dummy_all_measurements
from ...helpers.viewer_marker_colors import (
    MY_DATA_COLOR,
    MY_DATA_COLOR_NAME,
    MY_CLASS_COLOR,
    MY_CLASS_COLOR_NAME,
    OTHER_CLASSES_COLOR,
    OTHER_CLASSES_COLOR_NAME,
    OTHER_STUDENTS_COLOR,
    GENERIC_COLOR,
)
from ...remote import LOCAL_API
from ...story_state import (
    StoryState,
    ClassSummary,
    StudentMeasurement,
    StudentSummary,
    mc_callback,
    fr_callback,
    get_free_response,
    get_mc_response,
)
from ...tools import *  # noqa
from ...utils import (
    create_single_summary,
    make_summary_data,
    models_to_glue_data,
    get_image_path,
    push_to_route,
)
from ...viewers.hubble_histogram_viewer import HubbleHistogramView
from ...viewers.hubble_scatter_viewer import HubbleScatterView

logger = setup_logger("STAGE 5")


GUIDELINE_ROOT = Path(__file__).parent / "guidelines"


@solara.component
def Page(app_state: Reactive[AppState]):
    story_state = Ref(cast(StoryState, app_state.fields.story_state))
    stage_state = Ref(
        cast(
            StageState, story_state.fields.stage_states["class_results_and_uncertainty"]
        )
    )

    student_slider_setup, set_student_slider_setup = solara.use_state(False)
    class_slider_setup, set_class_slider_setup = solara.use_state(False)

    selected_student_id = solara.use_reactive(None)
    selected_class_id = solara.use_reactive(None)

    router = solara.use_router()
    location = solara.use_context(solara.routing._location_context)

    student_default_color = MY_CLASS_COLOR
    student_highlight_color = MY_DATA_COLOR

    class_default_color = OTHER_CLASSES_COLOR
    class_highlight_color = MY_CLASS_COLOR

    def _update_bins(
        viewers: Iterable[CDSHistogramView],
        _msg: Optional[NumericalDataChangedMessage] = None,
    ):
        props = ("hist_n_bin", "hist_x_min", "hist_x_max")
        with ExitStack() as stack:
            for viewer in viewers:
                stack.enter_context(delay_callback(viewer.state, *props))

            values = []
            for viewer in viewers:
                if viewer.layers:
                    # For now, we assume that the first layer contains the data that we're interested in
                    values.append(viewer.layers[0].layer[viewer.state.x_att])

            if not values:
                return

            try:
                xmin = round(min(min(vals) for vals in values), 0) - 2.5
                xmax = round(max(max(vals) for vals in values), 0) + 2.5
            except:
                return
            for viewer in viewers:
                viewer.state.hist_n_bin = int(xmax - xmin)
                viewer.state.hist_x_min = xmin
                viewer.state.hist_x_max = xmax

    force_memo_update = solara.use_reactive(False)
    data_ready = solara.use_reactive(False)

    def glue_setup() -> Tuple[JupyterApplication, Dict[str, PlotlyBaseView]]:
        # NOTE: use_memo has to be part of the main page render. Including it
        #  in a conditional will result in an error.
        gjapp = JupyterApplication(
            app_state.value.glue_data_collection, app_state.value.glue_session
        )

        if len(story_state.value.measurements) == 0:
            data_ready.set(False)
            return gjapp, {}

        layer_viewer = gjapp.new_data_viewer(HubbleScatterView, show=False)
        student_slider_viewer = gjapp.new_data_viewer(HubbleScatterView, show=False)
        class_slider_viewer = gjapp.new_data_viewer(HubbleScatterView, show=False)
        student_hist_viewer = gjapp.new_data_viewer(HubbleHistogramView, show=False)
        all_student_hist_viewer = gjapp.new_data_viewer(HubbleHistogramView, show=False)
        class_hist_viewer = gjapp.new_data_viewer(HubbleHistogramView, show=False)
        viewers = {
            "layer": layer_viewer,
            "student_slider": student_slider_viewer,
            "class_slider": class_slider_viewer,
            "student_hist": student_hist_viewer,
            "all_student_hist": all_student_hist_viewer,
            "class_hist": class_hist_viewer,
        }

        student_slider_viewer.state.reset_limits_from_visible = False
        class_slider_viewer.state.reset_limits_from_visible = False

        two_hist_viewers = (all_student_hist_viewer, class_hist_viewer)
        for att in ("x_min", "x_max"):
            link((all_student_hist_viewer.state, att), (class_hist_viewer.state, att))

        LOCAL_API.update_class_size(app_state)

        if not story_state.value.measurements_loaded:
            LOCAL_API.get_measurements(app_state, story_state)

        class_measurements = LOCAL_API.get_class_measurements(app_state, story_state)
        # if we are a teacher then our measurements were not loaded with class_measurements and only exist on the front end in local_state.value.measuements
        #  make sure we add these to the class_measurements
        if (not app_state.value.update_db) and len(story_state.value.measurements) > 0:
            class_measurements.extend(m for m in story_state.value.measurements)

        measurements = Ref(story_state.fields.class_measurements)
        student_ids = Ref(story_state.fields.stage_5_class_data_students)
        if class_measurements and not student_ids.value:
            ids = list(np.unique([m.student_id for m in class_measurements]))
            student_ids.set(ids)
        measurements.set(class_measurements)

        all_measurements, student_summaries, class_summaries = LOCAL_API.get_all_data(
            app_state, story_state
        )
        if app_state.value.classroom.class_info is not None:
            class_id = app_state.value.classroom.class_info["id"]
            class_distances = [
                distance
                for m in class_measurements
                if (
                    (distance := m.est_dist_value) is not None
                    and m.velocity_value is not None
                )
            ]
            class_velocities = [
                velocity
                for m in class_measurements
                if (
                    m.est_dist_value is not None
                    and (velocity := m.velocity_value) is not None
                )
            ]
            my_class_h0, my_class_age = create_single_summary(
                distances=class_distances, velocities=class_velocities
            )
            class_summaries.append(
                ClassSummary(
                    class_id=class_id,
                    hubble_fit_value=my_class_h0,
                    age_value=my_class_age,
                )
            )
            for measurement in class_measurements:
                measurement.class_id = class_id
            all_measurements.extend(class_measurements)

        all_meas = Ref(story_state.fields.all_measurements)
        all_stu_summaries = Ref(story_state.fields.student_summaries)
        all_cls_summaries = Ref(story_state.fields.class_summaries)
        all_meas.set(all_measurements)
        all_stu_summaries.set(student_summaries)
        all_cls_summaries.set(class_summaries)

        student_data = models_to_glue_data(
            story_state.value.measurements, label="My Data"
        )
        if not student_data.components:
            student_data = empty_data_from_model_class(
                StudentMeasurement, label="My Data"
            )
        student_data = app_state.value.add_or_update_data(student_data)

        class_ids = story_state.value.stage_5_class_data_students
        if (not app_state.value.update_db) and len(story_state.value.measurements) > 0:
            class_ids.append([m.student_id for m in story_state.value.measurements][0])
        class_data_points = [
            m for m in story_state.value.class_measurements if m.student_id in class_ids
        ]
        class_data = models_to_glue_data(class_data_points, label="Class Data")
        class_data = app_state.value.add_or_update_data(class_data)

        for component in ("est_dist_value", "velocity_value"):
            gjapp.add_link(student_data, component, class_data, component)
        layer_viewer.add_data(student_data)
        student_layer = layer_viewer.layers[0]
        student_layer.state.color = student_highlight_color
        student_layer.state.size = 12
        student_layer.state.zorder = 5

        layer_viewer.ignore(lambda data: data.label == "student_slider_subset")
        layer_viewer.add_data(class_data)
        class_layer = layer_viewer.layers[1]
        class_layer.state.zorder = 1
        class_layer.state.color = MY_CLASS_COLOR
        class_layer.state.size = 8
        class_layer.state.visible = False

        layer_viewer.state.x_att = class_data.id["est_dist_value"]
        layer_viewer.state.y_att = class_data.id["velocity_value"]
        layer_viewer.state.x_axislabel = "Distance (Mpc)"
        layer_viewer.state.y_axislabel = "Velocity (km/s)"
        layer_viewer.state.title = "Our Data"
        show_layer_traces_in_legend(layer_viewer)
        show_legend(layer_viewer, show=True)

        if len(class_data.subsets) == 0:
            student_slider_subset = class_data.new_subset(
                label="student_slider_subset", alpha=1, markersize=10
            )
        else:
            student_slider_subset = class_data.subsets[0]
        student_slider_viewer.add_data(class_data)
        student_slider_viewer.state.x_att = class_data.id["est_dist_value"]
        student_slider_viewer.state.y_att = class_data.id["velocity_value"]
        student_slider_viewer.state.x_axislabel = "Distance (Mpc)"
        student_slider_viewer.state.y_axislabel = "Velocity (km/s)"
        student_slider_viewer.state.title = "My Class Data"
        student_slider_viewer.add_subset(student_slider_subset)
        student_slider_viewer.layers[0].state.visible = False
        show_layer_traces_in_legend(student_slider_viewer)
        show_legend(student_slider_viewer, show=True)

        student_id = app_state.value.student.id
        class_summary_data = make_summary_data(
            class_data,
            input_id_field="student_id",
            output_id_field="id",
            label="Class Summaries",
        )
        class_summary_data = app_state.value.add_or_update_data(class_summary_data)
        if len(class_summary_data.subsets) == 0:
            my_summ_subset_state = RangeSubsetState(
                student_id, student_id, class_summary_data.id["id"]
            )
            my_summ_subset = class_summary_data.new_subset(
                subset=my_summ_subset_state,
                color="#FB5607",
                alpha=1,
                label="My Summary",
            )
        else:
            my_summ_subset = class_summary_data.subsets[0]

        my_measurements = story_state.value.measurements
        my_distances = [
            distance
            for m in my_measurements
            if (
                (distance := m.est_dist_value) is not None
                and m.velocity_value is not None
            )
        ]
        my_velocities = [
            velocity
            for m in my_measurements
            if (
                m.est_dist_value is not None
                and (velocity := m.velocity_value) is not None
            )
        ]
        my_h0, my_age = create_single_summary(
            distances=my_distances, velocities=my_velocities
        )
        student_summaries.append(
            StudentSummary(
                student_id=student_id, hubble_fit_value=my_h0, age_value=my_age
            )
        )

        student_hist_viewer.add_data(class_summary_data)
        student_hist_viewer.state.x_att = class_summary_data.id["age_value"]
        student_hist_viewer.state.x_axislabel = "Age (Gyr)"
        student_hist_viewer.state.title = "My class ages (5 galaxies each)"
        student_hist_viewer.layers[0].state.color = MY_CLASS_COLOR
        student_hist_viewer.add_subset(my_summ_subset)

        all_data = models_to_glue_data(all_measurements, label="All Measurements")
        all_data = app_state.value.add_or_update_data(all_data)

        student_summ_data = models_to_glue_data(
            student_summaries, label="All Student Summaries"
        )
        student_summ_data = app_state.value.add_or_update_data(student_summ_data)

        all_class_summ_data = models_to_glue_data(
            class_summaries, label="All Class Summaries"
        )
        all_class_summ_data = app_state.value.add_or_update_data(all_class_summ_data)

        if len(all_data.subsets) == 0:
            class_slider_subset = all_data.new_subset(
                label="class_slider_subset", alpha=1, markersize=10
            )
        else:
            class_slider_subset = all_data.subsets[0]

        class_slider_viewer.add_data(all_data)
        class_slider_viewer.state.x_att = all_data.id["est_dist_value"]
        class_slider_viewer.state.y_att = all_data.id["velocity_value"]
        class_slider_viewer.state.x_axislabel = "Distance (Mpc)"
        class_slider_viewer.state.y_axislabel = "Velocity (km/s)"
        class_slider_viewer.state.title = "All Classes Data"
        class_slider_viewer.layers[0].state.visible = False
        class_slider_viewer.add_subset(class_slider_subset)
        show_layer_traces_in_legend(class_slider_viewer)
        show_legend(class_slider_viewer, show=True)

        all_student_hist_viewer.add_data(student_summ_data)
        all_student_hist_viewer.state.x_att = student_summ_data.id["age_value"]
        all_student_hist_viewer.state.x_axislabel = "Age (Gyr)"
        all_student_hist_viewer.state.title = "All student ages (5 galaxies each)"
        all_student_hist_viewer.layers[0].state.color = OTHER_STUDENTS_COLOR

        class_hist_viewer.add_data(all_class_summ_data)
        class_hist_viewer.state.x_att = all_class_summ_data.id["age_value"]
        class_hist_viewer.state.x_axislabel = "Age (Gyr)"
        class_hist_viewer.state.title = "All class ages (~100 galaxies each)"
        class_hist_viewer.layers[0].state.color = OTHER_CLASSES_COLOR

        # This looks weird, and it kinda is!
        # The idea here is that the all students viewer will always have a wider range than the all classes viewer
        # So we force the home tool of the class viewer to limit-resetting based on the students viewer
        class_hist_viewer.toolbar.tools["plotly:home"].activate = (
            all_student_hist_viewer.toolbar.tools["plotly:home"].activate
        )

        for viewer in (student_hist_viewer, all_student_hist_viewer, class_hist_viewer):
            viewer.figure.update_layout(hovermode="closest")

        for viewer in viewers.values():
            viewer.state.reset_limits()

        gjapp.data_collection.hub.subscribe(
            gjapp.data_collection,
            NumericalDataChangedMessage,
            handler=partial(_update_bins, two_hist_viewers),
            filter=lambda msg: msg.data.label == "Student Summaries",
        )

        gjapp.data_collection.hub.subscribe(
            gjapp.data_collection,
            NumericalDataChangedMessage,
            handler=partial(_update_bins, [student_hist_viewer]),
            filter=lambda msg: msg.data.label
            in ("All Student Summaries", "All Class Summaries"),
        )

        data_ready.set(True)
        logger.info("Finished setting up glue viewers")
        return gjapp, viewers

    gjapp, viewers = solara.use_memo(glue_setup, dependencies=[force_memo_update.value])

    if not data_ready.value:
        rv.ProgressCircular(
            width=3,
            color="primary",
            indeterminate=True,
            size=100,
        )

        if app_state.value.show_team_interface:

            def fill_all_data():
                set_dummy_all_measurements(LOCAL_API, story_state, app_state)
                Ref(story_state.fields.measurements_loaded).set(True)
                force_memo_update.set(not force_memo_update.value)

            solara.Button(
                label="Fill in Sample Data",
                on_click=fill_all_data,
                classes=["demo-button"],
            )
            fill_all_data()
        return

    _update_bins((viewers["all_student_hist"], viewers["class_hist"]))
    _update_bins((viewers["student_hist"],))

    logger.info("DATA IS READY")
    for name, viewer in viewers.items():
        # We don't want to reset the class histogram's limits
        # as we let its limits be controlled by the student histogram
        # viewer's limits
        if name == "class_hist":
            continue
        viewer.state.reset_limits()

    def show_class_data(marker):
        if "Class Data" in app_state.value.glue_data_collection:
            class_data = app_state.value.glue_data_collection["Class Data"]
            layer = viewers["layer"].layer_artist_for_data(class_data)
            should_be_visible = marker >= Marker.cla_dat1
            if layer.state.visible is not should_be_visible:
                layer.state.visible = should_be_visible

    def show_student_data(marker):
        if "My Data" in app_state.value.glue_data_collection:
            student_data = app_state.value.glue_data_collection["My Data"]
            layer = viewers["layer"].layer_artist_for_data(student_data)
            should_be_visible = marker <= Marker.fin_cla1
            if layer.state.visible is not should_be_visible:
                layer.state.visible = should_be_visible

    def update_layer_viewer_visibilities(marker):
        with viewers["layer"].figure.batch_update():
            show_class_data(marker)
            show_student_data(marker)

    update_layer_viewer_visibilities(stage_state.value.current_step)

    class_best_fit_clicked = Ref(stage_state.fields.class_best_fit_clicked)

    uncertainty_step = Ref(stage_state.fields.uncertainty_state.step)
    uncertainty_max_step_completed = Ref(
        stage_state.fields.uncertainty_state.max_step_completed
    )

    def _on_best_fit_line_shown(active):
        if not class_best_fit_clicked.value:
            class_best_fit_clicked.set(active)

    def show_class_hide_my_age_subset(value):
        viewer = viewers["student_hist"]
        viewer.layers[0].state.visible = True  # in case student turned class off
        viewer.layers[1].state.visible = not value

    def _on_marker_updated(marker):
        if marker <= Marker.sho_mya1 or marker >= Marker.con_int2:
            show_class_hide_my_age_subset(True)

    def _state_callback_setup():
        current_step = Ref(stage_state.fields.current_step)
        current_step.subscribe(update_layer_viewer_visibilities)
        current_step.subscribe(_on_marker_updated)

    solara.use_memo(_state_callback_setup, dependencies=[])  # noqa: SH101

    line_fit_tool = viewers["layer"].toolbar.tools["hubble:linefit"]
    add_callback(line_fit_tool, "active", _on_best_fit_line_shown)

    def _jump_stage_6():
        push_to_route(router, location, "prodata")

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
                    label="Shortcut: Jump to Stage 6",
                    on_click=_jump_stage_6,
                    classes=["demo-button"],
                )

    def _parse_component_state():
        print("PARSE STATE")
        student_low_age = Ref(stage_state.fields.student_low_age)
        student_high_age = Ref(stage_state.fields.student_high_age)

        class_low_age = Ref(stage_state.fields.class_low_age)
        class_high_age = Ref(stage_state.fields.class_high_age)

        class_data_size = Ref(stage_state.fields.class_data_size)

        class_summary_data = app_state.value.glue_data_collection["Class Summaries"]
        student_low_age.set(round(min(class_summary_data["age_value"])))
        student_high_age.set(round(max(class_summary_data["age_value"])))
        class_data_size.set(len(class_summary_data["age_value"]))

        all_class_summ_data = app_state.value.glue_data_collection[
            "All Class Summaries"
        ]
        class_low_age.set(round(min(all_class_summ_data["age_value"])))
        class_high_age.set(round(max(all_class_summ_data["age_value"])))

    solara.use_memo(_parse_component_state, dependencies=[])  # noqa: SH101

    # --------------------- Row 1: OUR DATA HUBBLE VIEWER -----------------------
    if stage_state.value.current_step_between(
        Marker.ran_var1, Marker.fin_cla1
    ) or stage_state.value.current_step_between(Marker.cla_dat1, Marker.you_age1c):
        with solara.ColumnsResponsive(12, large=[5, 7]):
            with rv.Col():
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineRandomVariability.vue",
                    event_back_callback=lambda _: push_to_route(
                        router, location, "explore-data"
                    ),
                    event_next_callback=lambda _: transition_next(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    allow_back=False,
                    show=stage_state.value.is_current_step(Marker.ran_var1),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineFinishedClassmates.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.fin_cla1),
                    state_view={"class_data_size": stage_state.value.class_data_size},
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassData.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_dat1),
                    state_view={"class_data_size": stage_state.value.class_data_size},
                )

                # Skipping this guideline for now since we don't have linedraw functionality in glue viewer.
                # ScaffoldAlert(
                #     GUIDELINE_ROOT / "GuidelineTrendLinesDraw2c.vue",
                #     event_next_callback=lambda _: transition_next(COMPONENT_STATE),
                #     event_back_callback=lambda _: transition_previous(COMPONENT_STATE),
                #     can_advance=COMPONENT_STATE.value.can_transition(next=True),
                #     show=COMPONENT_STATE.value.is_current_step(Marker.tre_lin2c),
                # )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineBestFitLinec.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.bes_fit1c),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineYourAgeEstimatec.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.you_age1c),
                    state_view={
                        "low_guess": get_free_response(
                            "likely-low-age", stage_state
                        ).get("response"),
                        "high_guess": get_free_response(
                            "likely-high-age", stage_state
                        ).get("response"),
                        "best_guess": get_free_response(
                            "best-guess-age", stage_state
                        ).get("response"),
                    },
                )

            with rv.Col():
                ViewerLayout(viewer=viewers["layer"])

    # --------------------- Row 2: SLIDER VERSION: OUR DATA HUBBLE VIEWER -----------------------
    if stage_state.value.current_step_between(Marker.cla_res1, Marker.con_int3):
        with solara.ColumnsResponsive(12, large=[5, 7]):
            with rv.Col():
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassmatesResults.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_res1),
                    state_view={
                        "class_data_size": stage_state.value.class_data_size,
                        "my_color": MY_DATA_COLOR_NAME,
                        "my_class_color": MY_CLASS_COLOR_NAME,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineRelationshipAgeSlopeMC.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.rel_age1),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "mc_score": get_mc_response("age-slope-trend", stage_state),
                        "score_tag": "age-slope-trend",
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeRange.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_age1),
                    state_view={
                        "student_low_age": stage_state.value.student_low_age,
                        "student_high_age": stage_state.value.student_high_age,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeRange2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_age2),
                    state_view={
                        "student_low_age": stage_state.value.student_low_age,
                        "student_high_age": stage_state.value.student_high_age,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeRange3.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_age3),
                    state_view={
                        "student_low_age": stage_state.value.student_low_age,
                        "student_high_age": stage_state.value.student_high_age,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeRange4.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_age4),
                    state_view={
                        "student_low_age": stage_state.value.student_low_age,
                        "student_high_age": stage_state.value.student_high_age,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineLearnUncertainty1.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.lea_unc1),
                    state_view={
                        "uncertainty_slideshow_finished": stage_state.value.uncertainty_slideshow_finished,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineMostLikelyValue1.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.mos_lik1),
                )

            def update_student_slider_subset(id, highlighted):
                class_data = gjapp.data_collection["Class Data"]
                student_slider_subset = class_data.subsets[0]
                student_slider_subset.subset_state = RangeSubsetState(
                    id, id, class_data.id["student_id"]
                )
                color = (
                    student_highlight_color if highlighted else student_default_color
                )
                student_slider_subset.style.color = color
                student_slider_subset.style.markersize = 12
                if app_state.value.show_team_interface:
                    selected_student_id.set(id)
                if not student_slider_setup:
                    viewer = viewers["student_slider"]
                    viewer.state.reset_limits()
                    viewer.toolbar.tools["hubble:linefit"].activate()
                    set_student_slider_setup(True)

            with rv.Col(class_="no-padding"):
                ViewerLayout(viewer=viewers["student_slider"])
                class_summary_data = gjapp.data_collection["Class Summaries"]
                IdSlider(
                    gjapp=gjapp,
                    data=class_summary_data,
                    on_id=update_student_slider_subset,
                    highlight_ids=[app_state.value.student.id],
                    id_component=class_summary_data.id["id"],
                    value_component=class_summary_data.id["age_value"],
                    default_color=student_default_color,
                    highlight_color=student_highlight_color,
                )
                if app_state.value.show_team_interface:
                    rv.Chip(
                        children=[rv.Text(children=[f"Student ID {selected_student_id.value}"])],
                        style_="margin-top: 25px",
                    )

        if stage_state.value.current_step_between(Marker.lea_unc1, Marker.you_age1c):
            with solara.ColumnsResponsive(12, large=[5, 7]):
                with rv.Col():
                    pass
                with rv.Col():
                    # We show the free responses from the previous stage, so we need to
                    #  get the explore_data stage state to access these responses
                    stage_4_state = Ref(
                        cast(
                            StageState, story_state.fields.stage_states["explore_data"]
                        )
                    )
                    with rv.Col(cols=10, offset=1):
                        UncertaintySlideshow(
                            event_on_slideshow_finished=lambda _: Ref(
                                stage_state.fields.uncertainty_slideshow_finished
                            ).set(True),
                            step=stage_state.value.uncertainty_state.step,
                            max_step_completed=stage_state.value.uncertainty_state.max_step_completed,
                            age_calc_short1=get_free_response(
                                "shortcoming-1", stage_4_state
                            ).get("response"),
                            age_calc_short2=get_free_response(
                                "shortcoming-2", stage_4_state
                            ).get("response"),
                            age_calc_short_other=get_free_response(
                                "other-shortcomings", stage_4_state
                            ).get("response"),
                            event_fr_callback=lambda event: fr_callback(
                                event,
                                story_state,
                                stage_state,
                            ),
                            free_responses=[
                                get_free_response("shortcoming-4", stage_state),
                                get_free_response(
                                    "systematic-uncertainty", stage_state
                                ),
                            ],
                            event_set_step=uncertainty_step.set,
                            event_set_max_step_completed=uncertainty_max_step_completed.set,
                            image_location=get_image_path(router, "stage_five"),
                            show_team_interface=app_state.value.show_team_interface,
                        )

    # --------------------- Row 3: ALL DATA HUBBLE VIEWER - during class sequence -----------------------

    if stage_state.value.current_step_at_or_after(Marker.cla_res1c):
        with solara.ColumnsResponsive(12, large=[5, 7]):
            with rv.Col():
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassmatesResultsc.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_res1c),
                    state_view={
                        "my_class_color": MY_CLASS_COLOR_NAME,
                        "other_class_color": OTHER_CLASSES_COLOR_NAME,
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeRangec.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.cla_age1c),
                    state_view={
                        "class_low_age": stage_state.value.class_low_age,
                        "class_high_age": stage_state.value.class_high_age,
                    },
                )

            def update_class_slider_subset(id, highlighted):
                all_data = gjapp.data_collection["All Measurements"]
                class_slider_subset = all_data.subsets[0]
                class_slider_subset.subset_state = RangeSubsetState(
                    id, id, all_data.id["class_id"]
                )
                color = class_highlight_color if highlighted else class_default_color
                class_slider_subset.style.color = color
                if app_state.value.show_team_interface:
                    selected_class_id.set(id)
                if not class_slider_setup:
                    viewer = viewers["class_slider"]
                    viewer.state.reset_limits()
                    viewer.toolbar.tools["hubble:linefit"].activate()
                    set_class_slider_setup(True)

            with rv.Col():
                ViewerLayout(viewer=viewers["class_slider"])
                all_summary_data = gjapp.data_collection["All Class Summaries"]
                IdSlider(
                    gjapp=gjapp,
                    data=all_summary_data,
                    on_id=update_class_slider_subset,
                    highlight_ids=[app_state.value.classroom.class_info.get("id", 0)],
                    id_component=all_summary_data.id["class_id"],
                    value_component=all_summary_data.id["age_value"],
                    default_color=class_default_color,
                    highlight_color=class_highlight_color,
                )
                if app_state.value.show_team_interface:
                    rv.Chip(
                        children=[rv.Text(children=[f"Class ID {selected_class_id.value}"])],
                        style_="margin-top: 25px",
                    )

                with rv.Col(cols=10, offset=1):
                    UncertaintySlideshow(
                        event_on_slideshow_finished=lambda _: Ref(
                            stage_state.fields.uncertainty_slideshow_finished
                        ).set(True),
                        step=stage_state.value.uncertainty_state.step,
                        max_step_completed=stage_state.value.uncertainty_state.max_step_completed,
                        age_calc_short1=get_free_response(
                            "shortcoming-1", stage_state
                        ).get("response"),
                        age_calc_short2=get_free_response(
                            "shortcoming-2", stage_state
                        ).get("response"),
                        age_calc_short_other=get_free_response(
                            "other-shortcomings", stage_state
                        ).get("response"),
                        event_fr_callback=lambda event: fr_callback(
                            event, story_state, stage_state
                        ),
                        free_responses=[
                            get_free_response("shortcoming-4", stage_state),
                            get_free_response("systematic-uncertainty", stage_state),
                        ],
                        event_set_step=uncertainty_step.set,
                        event_set_max_step_completed=uncertainty_max_step_completed.set,
                        image_location=get_image_path(router, "stage_five"),
                        show_team_interface=app_state.value.show_team_interface,
                    )

    # --------------------- Row 4: OUR CLASS HISTOGRAM VIEWER -----------------------
    class_summary_data = gjapp.data_collection["Class Summaries"]

    def _on_percentage_selected_changed(_option, value):
        my_summ_subset = class_summary_data.subsets[0]
        my_summ_subset.style.alpha = 1 - int(value)

    if stage_state.value.current_step_between(Marker.age_dis1, Marker.con_int3):
        with solara.ColumnsResponsive(12, large=[5, 7]):
            with rv.Col():
                if stage_state.value.current_step_between(
                    Marker.mos_lik2, Marker.con_int3
                ):
                    with rv.Row():
                        with rv.Col():
                            StatisticsSelector(
                                viewers=[viewers["student_hist"]],
                                glue_data=[class_summary_data],
                                units=["Gyr"],
                                transform=round,
                                color=GENERIC_COLOR,
                            )

                        with rv.Col():
                            if stage_state.value.current_step_between(
                                Marker.con_int2, Marker.con_int3
                            ):
                                PercentageSelector(
                                    viewers=[viewers["student_hist"]],
                                    glue_data=[class_summary_data],
                                    units=["Gyr"],
                                    on_selected_changed=_on_percentage_selected_changed,
                                )

                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeDistribution.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.age_dis1),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineShowMyAgeDistribution.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.sho_mya1),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineMostLikelyValue2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.mos_lik2),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineMostLikelyValue3.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.mos_lik3),
                )

                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineConfidenceInterval.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.con_int1),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineConfidenceInterval2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.con_int2),
                )

            if stage_state.value.current_step_between(Marker.sho_mya1, Marker.con_int1):
                with rv.Col():
                    with rv.Row():

                        def _toggle_ignore(layer):
                            return layer.layer.label not in (
                                "My Summary",
                                "Class Summaries",
                            )

                        LayerToggle(
                            viewer=viewers["student_hist"],
                            layers=["Class Summaries", "My Summary"],
                            names={
                                "Class Summaries": "Class Ages",
                                "My Summary": "My Age",
                            },
                            ignore_conditions=[_toggle_ignore],
                        )

                    with rv.Row():
                        ViewerLayout(viewer=viewers["student_hist"])
            else:
                with rv.Col():
                    ViewerLayout(viewer=viewers["student_hist"])

    ScaffoldAlert(
        GUIDELINE_ROOT / "GuidelineMostLikelyValueReflect4.vue",
        event_next_callback=lambda _: transition_next(stage_state),
        event_back_callback=lambda _: transition_previous(stage_state),
        can_advance=stage_state.value.can_transition(next=True),
        show=stage_state.value.is_current_step(Marker.mos_lik4),
        event_fr_callback=lambda event: fr_callback(event, story_state, stage_state),
        state_view={
            "free_response_a": get_free_response("best-guess-age", stage_state),
            "free_response_b": get_free_response("my-reasoning", stage_state),
        },
    )

    ScaffoldAlert(
        GUIDELINE_ROOT / "GuidelineConfidenceIntervalReflect3.vue",
        event_next_callback=lambda _: transition_next(stage_state),
        event_back_callback=lambda _: transition_previous(stage_state),
        can_advance=stage_state.value.can_transition(next=True),
        show=stage_state.value.is_current_step(Marker.con_int3),
        event_fr_callback=lambda event: fr_callback(event, story_state, stage_state),
        state_view={
            "free_response_a": get_free_response("likely-low-age", stage_state),
            "free_response_b": get_free_response("likely-high-age", stage_state),
            "free_response_c": get_free_response("my-reasoning-2", stage_state),
        },
    )

    # --------------------- Row 5: ALL DATA HISTOGRAM VIEWER -----------------------

    if stage_state.value.current_step_between(Marker.age_dis1c):
        with solara.ColumnsResponsive(12, large=[5, 7]):
            with rv.Col():
                with rv.Row():
                    all_student_summary_data = gjapp.data_collection[
                        "All Student Summaries"
                    ]
                    all_class_summary_data = gjapp.data_collection[
                        "All Class Summaries"
                    ]
                    hist_viewers = [viewers["all_student_hist"], viewers["class_hist"]]
                    hist_data = [all_student_summary_data, all_class_summary_data]
                    units = ["Gyr" for _ in range(len(hist_viewers))]
                    with rv.Col():
                        StatisticsSelector(
                            viewers=hist_viewers,
                            glue_data=hist_data,
                            units=units,
                            transform=round,
                            color=GENERIC_COLOR,
                        )

                    with rv.Col():
                        PercentageSelector(
                            viewers=hist_viewers,
                            glue_data=hist_data,
                            units=units,
                        )

                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineClassAgeDistributionc.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.age_dis1c),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineTwoHistograms1.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.two_his1),
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineTwoHistogramsMC2.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.two_his2),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "mc_score": get_mc_response("histogram-range", stage_state),
                        "score_tag": "histogram-range",
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineTwoHistogramsMC3.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.two_his3),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "mc_score": get_mc_response(
                            "histogram-percent-range", stage_state
                        ),
                        "score_tag": "histogram-percent-range",
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineTwoHistogramsMC4.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.two_his4),
                    event_mc_callback=lambda event: mc_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "mc_score": get_mc_response(
                            "histogram-distribution", stage_state
                        ),
                        "score_tag": "histogram-distribution",
                    },
                )
                ScaffoldAlert(
                    GUIDELINE_ROOT / "GuidelineTwoHistogramsReflect5.vue",
                    event_next_callback=lambda _: transition_next(stage_state),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.two_his5),
                    event_fr_callback=lambda event: fr_callback(
                        event, story_state, stage_state
                    ),
                    state_view={
                        "free_response": get_free_response(
                            "unc-range-change-reasoning", stage_state
                        ),
                    },
                )
                ScaffoldAlert(
                    # TODO: event_next_callback should go to next stage but I don't know how to set that up.
                    GUIDELINE_ROOT / "GuidelineMoreDataDistribution.vue",
                    event_next_callback=lambda _: push_to_route(
                        router, location, "prodata"
                    ),
                    event_back_callback=lambda _: transition_previous(stage_state),
                    can_advance=stage_state.value.can_transition(next=True),
                    show=stage_state.value.is_current_step(Marker.mor_dat1),
                )

            with rv.Col():
                if stage_state.value.current_step_between(Marker.two_his1):
                    ViewerLayout(viewers["all_student_hist"])

                ViewerLayout(viewers["class_hist"])

        ScaffoldAlert(
            GUIDELINE_ROOT / "GuidelineConfidenceIntervalReflect2c.vue",
            event_next_callback=lambda _: transition_next(stage_state),
            event_back_callback=lambda _: transition_previous(stage_state),
            can_advance=stage_state.value.can_transition(next=True),
            show=stage_state.value.is_current_step(Marker.con_int2c),
            event_fr_callback=lambda event: fr_callback(
                event, story_state, stage_state
            ),
            state_view={
                "low_guess": get_free_response("likely-low-age", stage_state).get(
                    "response"
                ),
                "high_guess": get_free_response("likely-high-age", stage_state).get(
                    "response"
                ),
                "best_guess": get_free_response("best-guess-age", stage_state).get(
                    "response"
                ),
                "free_response_a": get_free_response(
                    "new-most-likely-age", stage_state
                ),
                "free_response_b": get_free_response("new-likely-low-age", stage_state),
                "free_response_c": get_free_response(
                    "new-likely-high-age", stage_state
                ),
                "free_response_d": get_free_response(
                    "my-updated-reasoning", stage_state
                ),
            },
        )
