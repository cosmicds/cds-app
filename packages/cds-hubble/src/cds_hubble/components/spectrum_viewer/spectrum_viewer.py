from typing import Callable, Optional

import plotly.graph_objects as go
import reacton.ipyvuetify as rv
import solara
from solara import Reactive

from ...story_state import StoryState
from ...story_state import GalaxyData
from pandas import DataFrame
from ...components.spectrum_viewer.plotly_figure import FigurePlotly
from cds_core.logger import setup_logger
from ...helpers.viewer_marker_colors import (
    GENERIC_COLOR,
    H_ALPHA_COLOR,
    MY_DATA_COLOR,
    LIGHT_GENERIC_COLOR,
)
from ...utils import PLOTLY_MARGINS
from ...remote import LOCAL_API
from astropy.table import Table


from glue_plotly.common import DEFAULT_FONT

logger = setup_logger("SPECTRUM")


@solara.component
def SpectrumViewer(
    galaxy_data: GalaxyData | None,
    obs_wave: float | None = None,
    spectrum_click_enabled: bool = False,
    show_obs_wave_line: bool = True,
    on_obs_wave_measured: Callable = None,
    on_rest_wave_tool_clicked: Callable = lambda: None,
    on_zoom_tool_clicked: Callable = lambda: None,
    on_zoom_tool_toggled: Callable = lambda: None,
    on_zoom: Callable = lambda: None,
    on_reset_tool_clicked: Callable = lambda: None,
    marker_position: Optional[solara.Reactive[float]] = None,
    on_set_marker_position: Callable = lambda x: None,
    spectrum_bounds: Optional[solara.Reactive[list[float]]] = None,
    on_spectrum_bounds_changed: Callable = lambda x: None,
    max_spectrum_bounds: Optional[solara.Reactive[list[float]]] = None,
    spectrum_color: str = GENERIC_COLOR,
    local_state: Reactive[StoryState] = None,
):

    # spectrum_bounds
    vertical_line_visible = solara.use_reactive(show_obs_wave_line)
    toggle_group_state = solara.use_reactive([])

    x_bounds = solara.use_reactive([])
    y_bounds = solara.use_reactive([])
    # spectrum_bounds = solara.use_reactive(spectrum_bounds or [], on_change=lambda x: x_bounds.set(x))
    if spectrum_bounds is not None:
        spectrum_bounds.subscribe(x_bounds.set)

    use_dark_effective = solara.use_trait_observe(solara.lab.theme, "dark_effective")

    def _load_spectrum():
        if galaxy_data is None:
            return False

        spec_data = LOCAL_API.load_spectrum_data(local_state, galaxy_data)

        return Table({"wave": spec_data.wave, "flux": spec_data.flux}).to_pandas()

    spec_data_task = solara.lab.use_task(
        _load_spectrum,
        dependencies=[galaxy_data],
    )

    if spec_data_task.finished and spec_data_task.value is not False:
        spec = spec_data_task.value
        logger.info("spec_data_task is finished")
        if (spec is not None) and (max_spectrum_bounds is not None):
            logger.info(
                f"\tSetting max_spectrum_bounds to {spec['wave'].min()} and {spec['wave'].max()}"
            )
            max_spectrum_bounds.set([spec["wave"].min(), spec["wave"].max()])

    def _rest_wave_tool_toggled():
        on_rest_wave_tool_clicked()

    def _on_relayout(event):
        if event is None:
            return

        try:
            x_bounds.set(
                [
                    event["relayout_data"]["xaxis.range[0]"],
                    event["relayout_data"]["xaxis.range[1]"],
                ]
            )
            # y_bounds.set(
            #     [
            #         event["relayout_data"]["yaxis.range[0]"],
            #         event["relayout_data"]["yaxis.range[1]"],
            #     ]
            # )
            toggle_group_state.set([x for x in toggle_group_state.value if x != 0])
        except:
            x_bounds.set([])
            y_bounds.set([])

        if "relayout_data" in event:
            if (
                "xaxis.range[0]" in event["relayout_data"]
                and "xaxis.range[1]" in event["relayout_data"]
            ):
                if spectrum_bounds is not None:
                    spectrum_bounds.set(
                        [
                            event["relayout_data"]["xaxis.range[0]"],
                            event["relayout_data"]["xaxis.range[1]"],
                        ]
                    )
                on_zoom()

    def _on_reset_button_clicked(*args, **kwargs):
        x_bounds.set([])
        y_bounds.set([])
        try:
            if spec_data_task.value is not None and spectrum_bounds is not None:
                spectrum_bounds.set(
                    [
                        spec_data_task.value["wave"].min(),
                        spec_data_task.value["wave"].max(),
                    ]
                )
        except Exception as e:
            logger.critical(f"Failed to reset spectrum bounds: {e}")

        on_reset_tool_clicked()

    solara.use_effect(_on_reset_button_clicked, dependencies=[galaxy_data])

    def _spectrum_clicked(**kwargs):
        if spectrum_click_enabled:
            vertical_line_visible.set(True)
            on_obs_wave_measured(kwargs["points"]["xs"][0])
        if marker_position is not None:
            # vertical_line_visible.set(False)
            value = kwargs["points"]["xs"][0]
            marker_position.set(value)
            on_set_marker_position(value)

    def _zoom_button_clicked():
        on_zoom_tool_clicked()
        on_zoom_tool_toggled()

    with rv.Card():
        with rv.Toolbar(class_="toolbar", dense=True):
            with rv.ToolbarTitle():
                solara.Text("SPECTRUM VIEWER")

            rv.Spacer()

            reset_button = solara.IconButton(
                v_on="tooltip.on",
                flat=True,
                tile=True,
                icon_name="mdi-cached",
                on_click=_on_reset_button_clicked,
            )

            rv.Tooltip(
                top=True,
                v_slots=[
                    {
                        "name": "activator",
                        "variable": "tooltip",
                        "children": rv.FabTransition(children=[reset_button]),
                    }
                ],
                children=["Reset View"],
            )

            with rv.BtnToggle(
                v_model=toggle_group_state.value,
                on_v_model=toggle_group_state.set,
                flat=True,
                tile=True,
                group=True,
                multiple=True,
            ):

                zoom_button = solara.IconButton(
                    v_on="tooltip.on",
                    icon_name="mdi-select-search",
                    on_click=_zoom_button_clicked,
                )

                rv.Tooltip(
                    top=True,
                    v_slots=[
                        {
                            "name": "activator",
                            "variable": "tooltip",
                            "children": rv.FabTransition(children=[zoom_button]),
                        }
                    ],
                    children=["Zoom wavelength axis"],
                )

                rest_wave_button = solara.IconButton(
                    v_on="tooltip.on",
                    icon_name="mdi-lambda",
                    on_click=_rest_wave_tool_toggled,
                )

                rv.Tooltip(
                    top=True,
                    v_slots=[
                        {
                            "name": "activator",
                            "variable": "tooltip",
                            "children": rv.FabTransition(children=[rest_wave_button]),
                        }
                    ],
                    children=["Show rest wavelength"],
                )

        if spec_data_task.value is None:
            with rv.Sheet(
                style_="height: 360px", class_="d-flex justify-center align-center"
            ):
                rv.ProgressCircular(size=100, indeterminate=True, color="primary")

            return
        elif not isinstance(spec_data_task.value, DataFrame):
            with rv.Sheet(
                style_="height: 360px", class_="d-flex justify-center align-center"
            ):
                solara.Text("Select a galaxy to view its spectrum")

            return

        if galaxy_data is None:
            logger.info("galaxy_data is None")
            return

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=spec_data_task.value["wave"],
                y=spec_data_task.value["flux"],
                line=dict(
                    color=spectrum_color,
                    width=2,
                ),
                mode="lines",
                hoverinfo="x",
            )
        )

        fig.update_layout(
            plot_bgcolor="white",
            font_family=DEFAULT_FONT,
            title_font_family=DEFAULT_FONT,
            margin=PLOTLY_MARGINS,
            yaxis=dict(
                linecolor="black",
                fixedrange=True,
                title="Brightness",
                showgrid=False,
                showline=True,
                linewidth=1,
                mirror=True,
                title_font_family=DEFAULT_FONT,
                title_font_size=16,
                tickfont_size=12,
                ticks="outside",
                ticklen=5,
                tickwidth=1,
                tickcolor="black",
            ),
            xaxis=dict(
                linecolor="black",
                title="Wavelength (Angstroms)",
                showgrid=False,
                showline=True,
                linewidth=1,
                mirror=True,
                title_font_family=DEFAULT_FONT,
                title_font_size=16,
                tickfont_size=12,
                hoverformat=".0f",
                ticks="outside",
                ticklen=5,
                tickwidth=1,
                tickcolor="black",
                ticksuffix=" Å",
            ),
            showlegend=False,
            hoverlabel=dict(
                font_size=16,
                bgcolor="white",
            ),
        )

        # This is the line that appears when user first makes observed wavelength measurement
        fig.add_vline(
            x=obs_wave,
            line_width=2,
            line_color=MY_DATA_COLOR,
            visible=vertical_line_visible.value
            and obs_wave > 0.0
            and spectrum_click_enabled,
        )

        # Orange "Your Measurement" Marker Line & Label
        fig.add_shape(
            type="line",
            x0=obs_wave,
            x1=obs_wave,
            y0=0.0,
            y1=0.2,
            xref="x",
            yref="paper",
            line_color=MY_DATA_COLOR,
            line_width=2,
            fillcolor=MY_DATA_COLOR,
            label={
                "text": f"Your measurement",
                "font": {
                    "color": MY_DATA_COLOR,
                    "family": "Arial, sans-serif",
                    "size": 14,
                    "weight": "bold",
                },
                "textposition": "bottom right",
                "xanchor": "left",
                "yanchor": "top",
                "textangle": 0,
            },
            visible=vertical_line_visible.value
            and obs_wave > 0.0
            and not spectrum_click_enabled,
        )

        # Light gray measurement line
        if (marker_position is not None) and (not spectrum_click_enabled):
            fig.add_vline(
                x=marker_position.value,
                line_width=2,
                line_color=LIGHT_GENERIC_COLOR,
                visible=True,
            )

        # Red Observed H-alpha Marker Line
        fig.add_shape(
            editable=False,
            x0=galaxy_data.redshift_rest_wave_value - 1.5,
            x1=galaxy_data.redshift_rest_wave_value + 1.5,
            y0=0.82,
            y1=0.99,
            yref="paper",
            xref="x",
            line_color=H_ALPHA_COLOR,
            fillcolor=H_ALPHA_COLOR,
            ysizemode="scaled",
        )

        # Red Observed H-alpha Marker Label
        fig.add_annotation(
            x=galaxy_data.redshift_rest_wave_value + 7,
            y=0.99,
            yref="paper",
            text=f"{galaxy_data.element} (observed)",
            showarrow=False,
            font=dict(
                family="Arial, sans-serif", size=14, color=H_ALPHA_COLOR, weight="bold"
            ),
            xanchor="left",
            yanchor="top",
        )

        # Black Rest H-alpha Marker Line
        fig.add_shape(
            editable=False,
            type="line",
            x0=galaxy_data.rest_wave_value,
            x1=galaxy_data.rest_wave_value,
            xref="x",
            y0=0.0,
            y1=1.0,
            line_color="black",
            ysizemode="scaled",
            yref="paper",
            line=dict(dash="dot", width=4),
            visible=1 in toggle_group_state.value,
        )

        # Black Rest H-alpha Marker Label
        fig.add_annotation(
            x=galaxy_data.rest_wave_value - 7,
            y=0.99,
            yref="paper",
            text=f"{galaxy_data.element} (rest)",
            showarrow=False,
            font=dict(
                family="Arial, sans-serif", size=14, color="black", weight="bold"
            ),
            xanchor="right",
            yanchor="top",
            visible=1 in toggle_group_state.value,
        )

        fig.update_layout(
            xaxis_zeroline=False,
            yaxis_zeroline=False,
            xaxis=dict(
                showspikes=True,
                # showline=spectrum_click_enabled,
                spikecolor="black",
                spikethickness=1,
                spikedash="solid",
                spikemode="across",
                spikesnap="cursor",
            ),
            spikedistance=-1,
            hovermode="x",
        )

        if x_bounds.value:  # and y_bounds.value:
            fig.update_xaxes(range=x_bounds.value)
            # fig.update_yaxes(range=y_bounds.value)
        # else:
        fig.update_yaxes(
            range=[
                spec_data_task.value["flux"].min() * 0.95,
                spec_data_task.value["flux"].max() * 1.25,
            ]
        )

        fig.update_layout(dragmode="zoom" if 0 in toggle_group_state.value else False)

        dependencies = [
            obs_wave,
            spectrum_click_enabled,
            vertical_line_visible.value,
            toggle_group_state.value,
            x_bounds.value,
            y_bounds.value,
        ]

        if marker_position is not None:
            dependencies.append(marker_position.value)

        FigurePlotly(
            fig,
            on_click=lambda kwargs: _spectrum_clicked(**kwargs),
            on_relayout=_on_relayout,
            dependencies=dependencies,
            config={"displayModeBar": False, "showTips": False},
        )
