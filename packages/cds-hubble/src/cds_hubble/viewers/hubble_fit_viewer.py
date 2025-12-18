from glue_plotly.viewers.scatter.viewer import PlotlyScatterView
from .hubble_scatter_viewer import HubbleScatterViewerState
from cds_core.viewers import cds_viewer

__all__ = [
    "HubbleFitLayerView",
]


HubbleFitLayerView = cds_viewer(
    PlotlyScatterView,
    name="HubbleFitLayerView",
    viewer_tools=[
        "hubble:linefit",
    ],
    label="Layer View",
    state_cls=HubbleScatterViewerState,
)
