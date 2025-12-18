from echo import delay_callback
from glue_plotly.viewers.scatter.viewer import PlotlyScatterView
from cds_core.viewers import CDSScatterViewerState
from cds_core.viewers import cds_viewer

__all__ = [
    "HubbleScatterView",
]


class HubbleScatterViewerState(CDSScatterViewerState):

    def reset_limits(self, visible_only=None):
        with delay_callback(self, "x_min", "x_max", "y_min", "y_max"):
            super().reset_limits(visible_only=visible_only)
            self.x_min = min(self.x_min, 0) if self.x_min is not None else 0
            self.y_min = min(self.y_min, 0) if self.y_min is not None else 0
            if self.x_max is not None:
                self.x_max = 1.1 * self.x_max
            if self.y_max is not None:
                self.y_max = 1.1 * self.y_max


HubbleScatterView = cds_viewer(
    PlotlyScatterView,
    name="HubbleScatterView",
    viewer_tools=["plotly:home", "plotly:zoom", "hubble:linefit"],
    label="Scatter View",
    state_cls=HubbleScatterViewerState,
)
