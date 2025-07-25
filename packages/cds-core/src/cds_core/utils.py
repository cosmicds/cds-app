from collections import Counter
from datetime import datetime
import json
from numbers import Number
import os
from math import log10
from types import UnionType
from glue.core import Component, ComponentID, Data, DataCollection
from glue.core.roi import CategoricalComponent
from glue_plotly.viewers import PlotlyBaseView
from pydantic import BaseModel
from pydantic.fields import FieldInfo
from requests import adapters
import random
from types import NoneType
from typing import Dict, Type, Union, get_args, get_origin

from IPython.display import Javascript, display

from astropy.modeling import models, fitting
from plotly.graph_objects import Scatter

from glue.core.state_objects import State
import numpy as np
from threading import Timer, Event
from functools import wraps
from traitlets import Unicode
from zmq.eventloop.ioloop import IOLoop
from enum import Enum

__all__ = [
    "load_template",
    "update_figure_css",
    "extend_tool",
    "convert_material_color",
    "fit_line",
    "line_mark",
    "vertical_line_mark",
    "API_URL",
    "CDSJSONEncoder",
    "RepeatedTimer",
    "debounce",
]

# The URL for the CosmicDS API
API_URL = "https://api.cosmicds.cfa.harvard.edu"

CDS_IMAGE_BASE_URL = (
    "https://cosmicds.github.io/cds-website/cosmicds_images/mean_median_mode"
)

DEFAULT_VIEWER_HEIGHT = 300


def get_session_id() -> str:
    """Returns the session id, which is stored using a browser cookie."""
    import solara.server.kernel_context

    context = solara.server.kernel_context.get_current_context()
    return context.session_id


# JC: I got parts of this from https://stackoverflow.com/a/57915246
class CDSJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        if isinstance(obj, State):
            return obj.as_dict()
        if isinstance(obj, datetime):
            return f"{obj}"
        if isinstance(obj, Enum):
            return obj.value
        return super(CDSJSONEncoder, self).default(obj)


# JC: I got this from https://stackoverflow.com/a/13151299
class RepeatedTimer(object):
    def __init__(self, interval, function, *args, **kwargs):
        self._timer = None
        self.interval = interval
        self.function = function
        self.args = args
        self.kwargs = kwargs
        self.is_running = False
        self.start()

    def _run(self):
        self.is_running = False
        loop = IOLoop()
        loop.make_current()
        self.start()
        self.function(*self.args, **self.kwargs)
        loop.close()

    def start(self):
        if not self.is_running:
            self._timer = Timer(self.interval, self._run)
            self._timer.start()
            self.is_running = True

    def stop(self):
        self._timer.cancel()
        self.is_running = False


def load_template(file_name, path=None, traitlet=False):
    """
    Load a vue template file and instantiate the appropriate traitlet object.

    Parameters
    ----------
    file_name : str
        The name of the template file.
    path : str
        The path to where the template file is stored. If none is given,
        assumes the directory where the python file calling this function
        resides.

    Returns
    -------
    `Unicode`
        The traitlet object used to hold the vue code.
    """
    path = os.path.dirname(path)

    with open(os.path.join(path, file_name)) as f:
        TEMPLATE = f.read()

    if traitlet:
        return Unicode(TEMPLATE)

    return TEMPLATE


def update_figure_css(viewer, style_dict=None, style_path=None):
    """
    Update the css of a BqPlot `~bqplot.figure.Figure` object.

    Parameters
    ----------
    viewer : `~glue_jupyter.bqplot.scatter.viewer.BqplotScatterView`
        The glue jupyter BqPlot viewer wrapper instance.
    style_dict : dict
        A dictionary containing the css attributes to be updated.
    style_path : string or `~pathlib.Path`
        A path to the ``.json`` file containing the css attributes to be
        parsed into a dictionary.
    """
    figure = viewer.figure_widget

    if style_path is not None:
        with open(style_path) as f:
            style_dict = json.load(f)

    fig_styles = style_dict.get("figure")
    viewer_styles = style_dict.get("viewer")

    # Update figure styles
    for k, v in fig_styles.items():
        # Update axes styles
        if k == "axes":
            for ak, av in fig_styles.get("axes")[0].items():
                if ak == "tick_values":
                    av = np.array(av)

                setattr(figure.axes[0], ak, av)

            for ak, av in fig_styles.get("axes")[1].items():
                if ak == "tick_values":
                    av = np.array(av)

                setattr(figure.axes[1], ak, av)
        else:
            setattr(figure, k, v)

    # Update viewer styles
    for prop in viewer_styles:
        for k, v in viewer_styles.get(prop, {}).items():
            is_list = isinstance(v, list)
            for index, layer in enumerate(viewer.layers):
                viewer_prop = getattr(layer, prop)
                val = v[index % len(v)] if is_list else v
                setattr(viewer_prop, k, val)


def extend_tool(
    viewer,
    tool_id,
    activate_cb=None,
    deactivate_cb=None,
    activate_before_tool=True,
    deactivate_before_tool=False,
):
    """
    This function extends the functionality of a tool on a viewer toolbar
    by adding callbacks that are activate upon tool item activation
    and deactivation.

    Parameters
    ----------
    viewer: `~glue.viewers.common.viewer.Viewer`
        The glue viewer whose tool we want to modify.
    tool_id: str
        The id of the tool that we want to modify - e.g. 'bqplot:xrange'
    activate_cb:
        The callback to be executed before or after the tool's `activate` method. Takes no arguments.
    deactivate_cb:
        The callback to be executed before or after the tool's `deactivate` method. Takes no arguments.
    activate_before_tool: bool
        Whether to run the inserted activate callback before the tool's `activate` method. If False, it runs after.
        Default is True.
    deactivate_before_tool: bool
        Whether to run the inserted activate callback before the tool's `deactivate` method. If False, it runs after.
        Default is False.

    """

    tool = viewer.toolbar.tools.get(tool_id, None)
    if not tool:
        return None

    activate = getattr(tool, "activate", lambda: None)
    deactivate = getattr(tool, "deactivate", lambda: None)

    def extended_activate():
        if activate_before_tool:
            activate_cb()
        activate()
        if not activate_before_tool:
            activate_cb()

    def extended_deactivate():
        if deactivate_before_tool:
            deactivate_cb()
        deactivate()
        if not deactivate_before_tool:
            deactivate_cb()

    if activate_cb:
        tool.activate = extended_activate
    if deactivate_cb:
        tool.deactivate = extended_deactivate


def convert_material_color(color_string):
    """
    This function converts the name of a material color, like those used in
    ipyvuetify (e.g. colors.<base>.<lighten/darken#>) into a hex code.
    """
    from .material_colors import MATERIAL_COLORS

    parts = color_string.split(".")[1:]
    result = MATERIAL_COLORS
    for part in parts:
        result = result[part]
    return result


def fit_line(x, y):
    fit = fitting.LinearLSQFitter()
    line_init = models.Linear1D(intercept=0, fixed={"intercept": True})
    fitted_line = fit(line_init, x, y)
    return fitted_line


def line_mark(start_x, start_y, end_x, end_y, color, label=None):
    """
    Creates a line between the given start and end points using Plotly's graphics objects.
    Parameters
    ----------
    start_x : int or float
        The x-coordinate of the line's starting point.
    start_y : int or float
        The y-coordinate of the line's starting point.
    end_x : int or float
        The x-coordinate of the line's endpoint.
    end_y : int or float
        The y-coordinate of the line's endpoint.
    color : str
        The desired color of the line, represented as a hex string.
    label : str, optional
        The label for the line. If provided, the line will be added to the legend.
    """
    line = Scatter(
        x=[start_x, end_x],
        y=[start_y, end_y],
        mode="lines",
        line=dict(color=color),
        name=label,
        showlegend=label is not None,
    )

    return line


def vertical_line_mark(layer, x, color, label=None):
    """
    A specialization of `line_mark` specifically for vertical lines.
    Parameters
    ----------
    layer : `glue.viewers.common.layer_artist.LayerArtist`
        The layer used to determine the line's scales.
    x : int or float
        The x-coordinate of the vertical line
    color : str
        The desired color of the line, represented as a hex string.
    """
    viewer_state = layer.state.viewer_state
    return line_mark(
        x,
        viewer_state.y_min,
        x,
        viewer_state.y_max,
        color,
        label=label,
    )


def debounce(wait):
    """
    Decorator that will postpone a function's execution until after `wait` seconds have elapsed
    since the last time it was invoked.
    """

    def decorator(fn):
        def debounced(*args, **kwargs):
            def call_it():
                return fn(*args, **kwargs)

            if hasattr(debounced, "_timer"):
                debounced._timer.cancel()

            debounced._timer = Timer(wait, call_it)
            debounced._timer.start()

        return debounced

    return decorator


def _debounce(wait):
    """
    Decorator that will postpone a function's execution until after `wait` seconds have elapsed
    since the last time it was invoked, and return the result of the function.
    """

    def decorator(fn):
        @wraps(fn)
        def debounced(*args, **kwargs):
            def call_it():
                debounced._result = fn(*args, **kwargs)
                debounced._called.set()

            if hasattr(debounced, "_timer"):
                debounced._timer.cancel()

            debounced._timer = Timer(wait, call_it)
            debounced._timer.start()

            debounced._called = Event()
            debounced._called.wait()

            return getattr(debounced, "_result", None)

        return debounced

    return decorator


def frexp10(x, normed=False):
    """
    Find the mantissa and exponent of a value in base 10.

    If normed is True, the mantissa is fractional, while it is between 0 and 10 if normed is False.
    Example:
        normed: 0.5 * 10^5
        non-normed: 5 * 10^4

    TODO: JC added this quickly mid-Hubble beta. Are there possible improvements?
    """
    exp = int(log10(x)) + int(normed)
    mantissa = x / (10**exp)
    return mantissa, exp


def percentile_index(size, percent, method=round):
    return min(method((size - 1) * percent / 100), size - 1)


def percent_around_center_indices(size, percent):
    """
    Compute the indices of the given percent around the center.
    """

    around_median = percent / 2
    bottom_percent = 50 - around_median
    top_percent = 50 + around_median

    bottom_index = percentile_index(size, bottom_percent)
    top_index = percentile_index(size, top_percent)
    return bottom_index, top_index


def mode(data, component_id, bins=None, range=None):
    """
    Compute the mode of a given dataset, using the component corresponding
    to the given ID. If bins are given, the data values will be binned
    before finding the modes. Bins should be specified as an integer (# bins)
    or sequence of scalars.
    """

    if bins is not None:
        hist = data.compute_histogram(
            [component_id], range=[range], bins=[len(bins) - 1]
        )
        indices = np.flatnonzero(hist == np.amax(hist))
        return [0.5 * (bins[idx] + bins[idx + 1]) for idx in indices]
    else:
        values = data[component_id]
        counter = Counter(values)
        max_count = counter.most_common(1)[0][1]
        return [k for k, v in counter.items() if v == max_count]


def component_type_for_field(info: FieldInfo) -> Type[Component]:
    if info.annotation is None:
        return Component  # TODO: What is the right result here?
    numerical = False
    if get_origin(info.annotation) in (Union, UnionType):
        types = get_args(info.annotation)
        numerical = all(t is NoneType or issubclass(t, Number) for t in types)
    elif issubclass(info.annotation, Number):
        numerical = True

    return Component if numerical else CategoricalComponent


def empty_data_from_model_class(cls: Type[BaseModel], label: str | None = None):
    data_dict = {}
    for field, info in cls.model_fields.items():
        if info.annotation is None:
            continue

        component_type = component_type_for_field(info)
        data_dict[field] = component_type(np.array([]))
    if label:
        data_dict["label"] = label
    return Data(**data_dict)


def basic_link_exists(
    data_collection: DataCollection, id1: ComponentID, id2: ComponentID
) -> bool:
    """NB: This only works for simple identity links."""
    ids = {id1, id2}
    return any(
        {link.get_from_ids()[0], link.get_to_id()} == ids
        for link in data_collection.links
    )


def make_figure_autoresize(figure, height=DEFAULT_VIEWER_HEIGHT):
    # The auto-sizing in the Plotly widget only works if the height
    # and width are undefined. First, unset the height and width,
    # then enable auto-sizing.
    figure.update_layout(height=None, width=None)
    figure.update_layout(autosize=True, height=height)


def combine_css(**kwargs):
    # append other args to the css string
    other = [f"{key.replace('_', '-')}:{value}" for key, value in kwargs.items()]
    css = ";".join(other)
    return css


def log_to_console(msg, css="color:white;"):
    display(Javascript(f'console.log("%c{msg}", "{css}");'))


class LoggingAdapter(adapters.HTTPAdapter):
    # https://requests.readthedocs.io/en/latest/user/advanced.html?#transport-adapters
    # https://requests.readthedocs.io/en/latest/user/advanced.html?#event-hooks
    def __init__(self, log_prefix=None, *args, **kwargs):
        self._log_prefix = log_prefix or str(random.randint(100, 999))
        super().__init__(*args, **kwargs)

    def set_prefix(self, prefix):
        self._log_prefix = prefix

    @staticmethod
    def clean_url(url):
        url = url.replace(API_URL, "")
        if "://" in url:
            url = "/".join(url.split("/")[3:])
        return url

    def send(self, request, *args, **kwargs):

        method = request.method
        url = self.clean_url(request.url)
        msg = f"Request: {method} {url}"

        if self._log_prefix:
            msg = f"({self._log_prefix}) {msg}"

        css = combine_css(color="royalblue")

        self.on_send(request)
        log_to_console(msg, css=css)
        return super().send(request, *args, **kwargs)

    def build_response(self, req, resp):
        response = super().build_response(req, resp)
        request = response.request
        method = request.method
        url = self.clean_url(request.url)
        status = response.status_code
        reason = response.reason

        msg = f"Response: {method} {url} {status} {reason}"
        if self._log_prefix:
            msg = f"({self._log_prefix}) {msg}"

        css = combine_css(
            color="green" if status < 400 else "red",
            font_weight=("bold" if status >= 400 else "normal"),
        )

        self.on_response(response)
        log_to_console(msg, css=css)
        return response

    @staticmethod
    def on_send(request):
        # needs to be given an implementation
        pass

    @staticmethod
    def on_response(response):
        # needs to be given an implementation
        pass


def show_legend(viewer: PlotlyBaseView, show: bool = True):
    layout_update: Dict = {"showlegend": show}
    if show:
        layout_update["legend"] = {
            "yanchor": "top",
            "xanchor": "left",
            "y": 0.99,
            "x": 0.01,
        }
    viewer.figure.update_layout(**layout_update)
    return


def show_layer_traces_in_legend(viewer: PlotlyBaseView, show: bool = False):
    for layer in viewer.layers:
        for trace in layer.traces():
            trace.update(showlegend=show)
