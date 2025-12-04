from echo import CallbackProperty
from glue.config import viewer_tool
from glue_plotly.viewers.common.tools import PlotlyHZoomMode

from cds_core.config import register_tool


@register_tool
class WavelengthZoom(PlotlyHZoomMode):
    icon = "glue_zoom_to_rect"
    mdi_icon = "mdi-select-search"
    tool_id = "hubble:wavezoom"
    action_text = "x axis zoom"
    tool_tip = "Zoom in on a region of the x-axis"
    zoom_tool_activated = CallbackProperty(False)

    on_zoom = None

    def _on_selection(self, _trace, _points, selector):
        state = self.viewer.state
        xbounds_old = [state.x_min, state.x_max]
        super()._on_selection(_trace, _points, selector)
        if self.on_zoom is not None:
            xbounds_new = [state.x_min, state.x_max]
            self.on_zoom(xbounds_old, xbounds_new)
