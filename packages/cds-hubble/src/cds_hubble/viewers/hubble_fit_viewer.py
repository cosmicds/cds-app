from echo import delay_callback
from glue_plotly.viewers.scatter.viewer import PlotlyScatterView
from .hubble_scatter_viewer import HubbleScatterViewerState
from cds_core.viewers import cds_viewer

__all__ = [
    "HubbleFitView",
    "HubbleFitLayerView",
]


class HubbleFitViewerState(HubbleScatterViewerState):

    def reset_limits(self, visible_only=None):
        with delay_callback(self, "x_min", "x_max", "y_min", "y_max"):
            super().reset_limits(visible_only=visible_only)
            if self.x_max is not None:
                self.x_max = 1.1 * self.x_max
            if self.y_max is not None:
                self.y_max = 1.1 * self.y_max


HubbleFitView = cds_viewer(
    PlotlyScatterView,
    name="HubbleFitView",
    viewer_tools=["plotly:home", "plotly:zoom", "hubble:linefit"],
    label="Fit View",
    state_cls=HubbleFitViewerState,
)

HubbleFitLayerView = cds_viewer(
    PlotlyScatterView,
    name="HubbleFitLayerView",
    viewer_tools=[
        "hubble:linefit",
    ],
    label="Layer View",
    state_cls=HubbleFitViewerState,
)
