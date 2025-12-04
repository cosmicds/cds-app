from random import randint
from cds_core.viewers.dotplot.viewer import DotplotScatterLayerArtist

import solara
from glue.core import Data, Subset
from reacton import ipyvuetify as rv

from ...viewers.hubble_dotplot import HubbleDotPlotView, HubbleDotPlotViewer
from cds_core.viewers.dotplot.state import DotPlotViewerState

from glue.viewers.common.viewer import Viewer
from glue_plotly.viewers.common.viewer import PlotlyBaseView
from cds_core.utils import vertical_line_mark, extend_tool
from ...utils import PLOTLY_MARGINS
from ...helpers.viewer_marker_colors import LIGHT_GENERIC_COLOR
from itertools import chain
from uuid import uuid4
from plotly.graph_objects import Scatter
import plotly.graph_objects as go
from numbers import Number
from typing import Callable, Iterable, List, cast, Union, Optional
from solara.toestand import Reactive
import numpy as np


from cds_core.logger import setup_logger

logger = setup_logger("DOTPLOT")

from glue_jupyter import JupyterApplication


def is_valid_range(arr: Union[None, list]):
    # is it None or not an iterable?
    if arr is None or not hasattr(arr, "__iter__"):
        return False
    if len(arr) != 2:
        return False
    # check for bad value: None, not a number, or inf, nan
    if any(x is None for x in arr):
        return False
    if not all(isinstance(x, (int, float)) for x in arr):
        return False
    if any(not np.isfinite(x) for x in arr):
        return False
    return True


def different_value(arr, value, index):
    if not is_valid_range(arr):
        return True
    return arr[index] != value


def this_or_default(arr, default, index):
    if not is_valid_range(arr):
        return default
    return arr[index]


def set_viewer_x_range(viewer: HubbleDotPlotViewer, x_min: float, x_max: float):
    """
    Set the x range of the viewer
    """

    order = [("x_min", x_min), ("x_max", x_max)]
    max_first = (
        viewer.state.x_max is not None
        and x_min is not None
        and viewer.state.x_max <= x_min
    )
    if max_first:
        order.reverse()
    for name, value in order:
        if value is not None:
            setattr(viewer.state, name, value)


_original_update_data = DotplotScatterLayerArtist._update_data


@solara.component
def DotplotViewer(
    gjapp: JupyterApplication,
    data=None,
    component_id=None,
    title=None,
    height=300,
    on_click_callback=None,
    line_marker_at: Optional[float | int] = None,  # type: ignore
    on_line_marker_at_changed: Callable = lambda x: None,
    line_marker_color=LIGHT_GENERIC_COLOR,
    vertical_line_visible: bool = True,  # type: ignore
    on_vertical_line_visible_changed: Callable = lambda x: None,
    unit: Optional[str] = None,
    x_label: Optional[str] = None,
    y_label: Optional[str] = None,
    nbin: int = 75,
    nbin_func: Optional[Callable] = None,
    x_bounds: list[float] = [],  # type: ignore
    on_x_bounds_changed: Callable = lambda x: None,
    reset_bounds: list = [],  # type: ignore
    on_reset_bounds_changed: Callable = lambda x: None,
    hide_layers: List[Data | Subset] = [],  # type: ignore
    on_hide_layers_changed: Callable = lambda x: None,
):
    """
    DotplotViewer component

    Basic Usage:
    ```python
    data = Data(label = "Test Data", x=[randint(1, 10) for _ in range(30)])
    DotplotViewer(data = data, component_id: str = 'x')
    ```

    Parameters:
    - `gjapp`: The GlueJupyter application instance
    - `data`: The data to be displayed in the viewer. Can be a single Data object or a list of Data objects.
    - `component_id`: The component id of the data to be displayed. Only used if `data` is a list of Data objects.
       the components should already linked. component_id is the id for the first (only) Data object in the list.
    - `title`: The title of the viewer
    - `height`: The height of the viewer (default: 400)
    - `on_click_callback`: A callback function that is called when a point is clicked. The function should accept the
    - `line_marker_at`: The value at which the vertical line marker should be placed (passed value is displayed)
    - `line_marker_color`: The color of the vertical line marker (default: 'red')
    - `vertical_line_visible`: Whether the vertical line marker should be visible (default: True)
    - `unit`: The unit for the x-axis values, used in the label for the vertical line (default: None)
    - `x_label`: x_label (Optional[str]): The label for the x-axis of the dot plot. If None, the label will be the name of the x attribute.
    - `y_label`: y_label (Optional[str]): The label for the y-axis of the dot plot. If None, the label will be the name of the y attribute.

    """

    logger.info(f"creating DotplotViewer: {title}")
    x_bounds: Reactive[list] = solara.use_reactive(x_bounds, on_change=on_x_bounds_changed)  # type: ignore
    vertical_line_visible: Reactive[bool] = solara.use_reactive(vertical_line_visible, on_change=on_vertical_line_visible_changed)  # type: ignore
    line_marker_at: Reactive[Number] = solara.use_reactive(line_marker_at, on_change=on_line_marker_at_changed)  # type: ignore
    reset_bounds: Reactive[list] = solara.use_reactive(reset_bounds, on_change=on_reset_bounds_changed)  # type: ignore
    hide_layers: Reactive[list] = solara.use_reactive(hide_layers, on_change=on_hide_layers_changed)  # type: ignore

    if len(x_bounds.value) == 0 and is_valid_range(reset_bounds.value):
        x_bounds.set(reset_bounds.value)

    with rv.Card() as main:
        with rv.Toolbar(dense=True, class_="toolbar"):
            with rv.ToolbarTitle(class_="toolbar toolbar-title"):
                title_container = rv.Html(tag="div")

            rv.Spacer()
            toolbar_container = rv.Html(tag="div")

        viewer_container = rv.Html(
            tag="div", style_=f"width: 100%; height: {height}px", class_="mb-4"
        )

        def _add_vertical_line(
            viewer: PlotlyBaseView,
            value: Number,
            color: str,
            label: str = None,
            line_ids: list[str] = [],
        ):
            line_id = str(uuid4())
            # print(line_id)
            line_ids.append(line_id)
            viewer.figure.add_vline(
                x=value,
                line_color=color,
                line_width=2,
                name=line_id,
                visible=vertical_line_visible.value,
            )

        def _add_data(viewer: PlotlyBaseView, data: Union[Data, tuple]):
            if isinstance(data, Data):
                logger.info(f"{title}: Adding data: {data.label}")
                viewer.add_data(data)
            else:
                logger.info(f"{title}: Adding data: {data.label}")
                viewer.add_data(data[0], layer_type=data[1])

        def _add_viewer():
            logger.info(f"{title}: _add_viewer()")
            if data is None:
                viewer_data = Data(
                    label="Test Data", x=[randint(1, 10) for _ in range(30)]
                )
                gjapp.data_collection.append(viewer_data)
            else:
                if isinstance(data, Data):
                    viewer_data = data
                else:
                    viewer_data = data[0]

            dotplot_view: HubbleDotPlotViewer = gjapp.new_data_viewer(
                HubbleDotPlotView, show=False
            )  # type: ignore

            _add_data(dotplot_view, viewer_data)
            if isinstance(viewer_data, tuple):
                viewer_data = viewer_data[0]

            if component_id is not None:
                dotplot_view.state.x_att = viewer_data.id[component_id]

            if isinstance(data, list):
                if len(data) > 1:
                    for viewer_data in data[1:]:
                        _add_data(dotplot_view, viewer_data)

            dotplot_view.state.hist_n_bin = nbin
            if is_valid_range(x_bounds.value):
                set_viewer_x_range(dotplot_view, x_bounds.value[0], x_bounds.value[1])

            if nbin_func is not None:
                dotplot_view.state.hist_n_bin = nbin_func(
                    dotplot_view.state.x_min, dotplot_view.state.x_max
                )

            for layer in dotplot_view.layers:
                for trace in layer.traces():
                    trace.update(hoverinfo="skip", hovertemplate=None)

            # this doesn't even get run;
            def no_hover_update(self: DotplotScatterLayerArtist):
                logger.info(f"{title}: no_hover_update")
                hide_ignored_layers()
                with dotplot_view.figure.batch_update():
                    _original_update_data(self)
                    for trace in self.traces():
                        trace.update(hoverinfo="skip", hovertemplate=None)
                    self._update_zorder()

            DotplotScatterLayerArtist._update_data = no_hover_update

            def get_layer(layer_name):
                layer_artist = dotplot_view.layer_artist_for_data(layer_name)  # type: ignore
                if layer_artist is None:
                    logger.warning(f"{title}: Layer not found: {layer_name}")
                return layer_artist

            def hide_ignored_layers(*args):
                logger.info(f"{title}: Hiding ignored layers")
                layers = dotplot_view.layers
                hidden_layers = [get_layer(l) for l in hide_layers.value]  # type: ignore
                # visible_layers = [l for l in layers if l not in hidden_layers]
                for layer in hidden_layers:
                    if layer is not None:
                        logger.info(f"({title}): Hiding: {layer.layer.label}")
                        layer.visible = False
                for layer in layers:
                    if (layer is not None) and not layer in hidden_layers:
                        logger.info(f"({title}): Showing: {layer.layer.label}")
                        layer.visible = True

            # override the default selection layer
            def new_update_selection(self=dotplot_view):
                state = cast(DotPlotViewerState, self.state)
                x0 = state.x_min
                dx = (state.x_max - state.x_min) * 0.005
                y0 = state.y_min
                dy = (state.y_max - state.y_min) * 2
                self.selection_layer.update(x0=x0 - dx, dx=dx, y0=y0, dy=dy)

            dotplot_view._update_selection_layer_bounds = new_update_selection

            if x_label is not None:
                dotplot_view.state.x_axislabel = x_label

            if y_label is not None:
                dotplot_view.state.y_axislabel = y_label

            line_ids = []  # [_line_ids_for_viewer(dotplot_view)]

            def _update_lines(value=None):
                if value is not None:
                    if len(line_ids) > 0:
                        dotplot_view.figure.update_shapes(
                            patch=dict(
                                visible=vertical_line_visible.value
                                and value is not None,
                                x0=value,
                                x1=value,
                            ),
                            selector={"name": line_ids[0]},
                        )
                    elif len(line_ids) == 0:
                        _add_vertical_line(
                            dotplot_view,
                            value,
                            line_marker_color,
                            label="Line Marker",
                            line_ids=line_ids,
                        )
                elif len(line_ids) > 0:
                    dotplot_view.figure.update_shapes(
                        patch=dict(visible=vertical_line_visible.value),
                        selector={"name": line_ids[0]},
                    )

            if title is not None:
                dotplot_view.state.title = title

            title_widget = solara.get_widget(title_container)
            title_widget.children = (dotplot_view.state.title or "DOTPLOT VIEWER",)

            toolbar_widget = solara.get_widget(toolbar_container)
            toolbar_widget.children = (dotplot_view.toolbar,)

            viewer_widget = solara.get_widget(viewer_container)
            viewer_widget.children = (dotplot_view.figure_widget,)

            # The auto sizing in the plotly widget only works if the height
            #  and width are undefined. First, unset the height and width,
            #  then enable auto sizing.
            dotplot_view.figure_widget.update_layout(height=None, width=None)
            dotplot_view.figure_widget.update_layout(autosize=True, height=height)
            dotplot_view.figure_widget.update_layout(
                margin=PLOTLY_MARGINS,
                showlegend=False,
                hovermode="x",
                clickmode="event",
                spikedistance=-1,
                xaxis=dict(
                    spikecolor="black",
                    spikethickness=1,
                    spikedash="solid",
                    spikemode="across",
                    spikesnap="cursor",
                    showspikes=True,
                    tickformat=",.0f",
                    title_font_size=16,
                ),
                yaxis=dict(
                    tickmode="auto",
                    title_font_size=16,
                ),
                hoverlabel=dict(
                    bgcolor="white",
                    font_size=16,
                ),
            )

            def on_click(trace, points, selector):
                if len(points.xs) > 0:
                    value = points.xs[0]
                    _update_lines(value=value)
                    if on_click_callback is not None:
                        on_click_callback(points)
                else:
                    logger.info(f"{title}: No points selected")

            dotplot_view.selection_layer.on_click(on_click)
            unit_str = f" {unit}" if unit else ""
            dotplot_view.selection_layer.update(
                hovertemplate=f"%{{x:,.0f}}{unit_str}<extra></extra>", hoverinfo="x"
            )

            def reset_selection():
                dotplot_view.set_selection_active(True)
                # special treatment for go.Heatmap from https://stackoverflow.com/questions/58630928/how-to-hide-the-colorbar-and-legend-in-plotly-express-bar-graph#comment131880779_68555667
                dotplot_view.selection_layer.update(
                    visible=True, z=[list(range(201))], opacity=0, coloraxis="coloraxis"
                )
                dotplot_view.figure.update_coloraxes(showscale=False)

            def _on_reset_bounds(*args):
                if None not in reset_bounds.value and len(reset_bounds.value) == 2:
                    new_range = reset_bounds.value
                    set_viewer_x_range(dotplot_view, new_range[0], new_range[1])
                else:
                    new_range = [dotplot_view.state.x_min, dotplot_view.state.x_max]

                if (
                    is_valid_range(x_bounds.value)
                    and not np.isclose(x_bounds.value, new_range).all()
                ):
                    logger.info(
                        f"{title}: reset x_bounds ({new_range[0]:0.2f}, {new_range[1]:0.2f})"
                    )
                    x_bounds.set(new_range)
                else:
                    logger.info(f"{title}: Bounds already set")

            def _on_wavezoom(*args):
                logger.info(f"{title}: Zoomed")
                new_range = [dotplot_view.state.x_min, dotplot_view.state.x_max]
                if (
                    not is_valid_range(x_bounds.value)
                    or not np.isclose(x_bounds.value, new_range).all()
                ):
                    logger.info(
                        f"{title}: set x_bounds ({new_range[0]:0.2f}, {new_range[1]:0.2f})"
                    )
                    x_bounds.set(new_range)
                else:
                    logger.info(f"{title}: Bounds already set")

            def extend_the_tools():
                extend_tool(
                    dotplot_view,
                    "hubble:wavezoom",
                    deactivate_cb=_on_wavezoom,
                )

            extend_the_tools()
            tool = dotplot_view.toolbar.tools["plotly:home"]
            if tool:
                tool.activate()
                old_activate = tool.activate

                def new_activate():
                    if len(reset_bounds.value) == 2:
                        _on_reset_bounds()
                    else:
                        old_activate()

                tool.activate = new_activate

            zoom_tool = dotplot_view.toolbar.tools["hubble:wavezoom"]

            def on_zoom(bounds_old, bounds_new):
                dotplot_view.state._update_bins()

            zoom_tool.on_zoom = on_zoom

            reset_bounds.subscribe(lambda x: tool.activate())

            if line_marker_at.value is not None:
                _update_lines(value=line_marker_at.value)

            line_marker_at.subscribe(lambda new_val: _update_lines(value=new_val))
            vertical_line_visible.subscribe(lambda new_val: _update_lines())

            def reset_hist_n_bin(xmin=None, xmax=None):
                set_viewer_x_range(dotplot_view, xmin, xmax)
                if is_valid_range([xmin, xmax]):
                    dotplot_view.state.hist_n_bin = nbin_func(xmin, xmax)

            def update_x_bounds(new_val):
                logger.info(f"{title}: Updating x_bounds")
                if is_valid_range(new_val):
                    set_viewer_x_range(dotplot_view, new_val[0], new_val[1])
                reset_hist_n_bin(new_val[0], new_val[1])
                reset_selection()

            x_bounds.subscribe(update_x_bounds)

            home_tool = dotplot_view.toolbar.tools["plotly:home"]
            home_tool.activate()

            reset_selection()

            hide_ignored_layers()
            hide_layers.subscribe(hide_ignored_layers)

            def cleanup():
                for cnt in (title_widget, toolbar_widget, viewer_widget):
                    cnt.children = ()

                for wgt in (dotplot_view.toolbar, dotplot_view.figure_widget):
                    # wgt.layout.close()
                    wgt.close()

            return cleanup

        solara.use_effect(_add_viewer, dependencies=[])

    return main
