from typing import Callable, Optional

import astropy.units as u
import solara
from astropy.coordinates import SkyCoord
from astropy.table import Table
from reacton import ipyvuetify as rv
from solara import Reactive

from ...remote import LOCAL_API
from ...story_state import StoryState
from ...utils import GALAXY_FOV
from ...widgets.hubble_wwt import HubbleWWTWidget

SDSS = "SDSS9 color"
DSS = "Digitized Sky Survey (Color)"

UPDATE_TIME = 1  # seconds
INIT_COORDINATE = SkyCoord(170 * u.deg, 13.3 * u.deg, frame="icrs")
START_COORDINATES = SkyCoord(180 * u.deg, 25 * u.deg, frame="icrs")


@solara.component
def SelectionTool(
    local_state: Reactive[StoryState],
    show_galaxies: bool,
    galaxy_selected_callback: Callable,
    galaxy_added_callback: Callable,
    deselect_galaxy_callback: Callable,
    background_counter: solara.Reactive[int],
    selected_galaxy: Optional[dict] = None,
    candidate_galaxy: Optional[dict] = None,
    on_wwt_ready: Optional[Callable] = None,
):
    show_wwt = solara.use_reactive(False)
    selected = solara.use_reactive(candidate_galaxy)
    current_layer = solara.use_reactive(None)
    reset_view = solara.use_reactive(False)
    refresh_images = solara.use_reactive(False)
    motions_left, set_motions_left = solara.use_state(2)

    with rv.Card() as main:
        with rv.Card(color="info", class_="pa-1" if show_galaxies else ""):
            with rv.Toolbar(dense=True, class_="toolbar"):
                rv.ToolbarTitle(children=["COSMIC SKY VIEWER"])
                rv.Spacer()

            with rv.Html(
                tag="div",
                style_="position: relative; height: 400px; width: 100%",
                class_="selection-content",
            ):
                wwt_container = rv.Html(tag="div")

                if not show_wwt.value:
                    with rv.Overlay(absolute=True, opacity=1):
                        rv.ProgressCircular(
                            size=100, color="primary", indeterminate=True
                        )

                if selected.value is not None:

                    def _on_galaxy_added():
                        galaxy_added_callback(selected.value)
                        selected.set(None)
                        deselect_galaxy_callback()

                    # Add galaxy button
                    add_gal_btn = solara.Button(
                        v_on="tooltip.on",
                        color="var(--success-dark)",
                        classes=["selection-fab", "black--text"],
                        fab=True,
                        bottom=True,
                        left=True,
                        absolute=True,
                        style="--margin: 15px; --card-padding: 16px; bottom: 0px !important; margin-bottom: var(--margin); margin-left: calc(var(--margin) - var(--card-padding));",
                        children=[rv.Icon(children=["mdi-plus"])],
                        on_click=_on_galaxy_added,
                    )

                    rv.Tooltip(
                        top=True,
                        v_slots=[
                            {
                                "name": "activator",
                                "variable": "tooltip",
                                "children": rv.FabTransition(children=[add_gal_btn]),
                            }
                        ],
                        children=["Add Galaxy to the Dataset"],
                    )

                # Reset view button
                reset_view_btn = solara.Button(
                    v_on="tooltip.on",
                    color="var(--success-dark)",
                    classes=["selection-fab", "black--text"],
                    fab=True,
                    bottom=True,
                    right=True,
                    absolute=True,
                    style="--margin: 15px; --card-padding: 16px; bottom: 0px !important; margin-bottom: var(--margin); margin-right: calc(var(--margin) - var(--card-padding));",
                    children=[rv.Icon(children=["mdi-cached"])],
                    on_click=lambda: reset_view.set(not reset_view.value),
                )

                rv.Tooltip(
                    top=True,
                    v_slots=[
                        {
                            "name": "activator",
                            "variable": "tooltip",
                            "children": rv.FabTransition(children=[reset_view_btn]),
                        }
                    ],
                    children=["Reset View"],
                )

                # Refresh images button
                if selected.value is not None:
                    refresh_images_btn = solara.Button(
                        v_on="tooltip.on",
                        color="#CCCCCC",
                        classes=["selection-fab", "black--text"],
                        fab=True,
                        top=True,
                        right=True,
                        absolute=True,
                        style_="--margin: 15px; --card-padding: 16px; top: 0px !important; margin-top: var(--margin); margin-right: calc(var(--margin) - var(--card-padding));",
                        children=[rv.Icon(children=["mdi-refresh"])],
                        on_click=lambda: refresh_images.set(not refresh_images.value),
                    )

                    rv.Tooltip(
                        top=True,
                        v_slots=[
                            {
                                "name": "activator",
                                "variable": "tooltip",
                                "children": rv.FabTransition(
                                    children=[refresh_images_btn]
                                ),
                            }
                        ],
                        children=["Refresh Images"],
                    )

    def _add_widget():
        """
        Add the WWT widget to the container.
        """
        wwt_widget = HubbleWWTWidget(use_remote=True)
        wwt_widget.observe(lambda change: show_wwt.set(change["new"]), "_wwt_ready")

        wwt_widget_container = solara.get_widget(wwt_container)
        wwt_widget_container.children = (wwt_widget,)

        def _on_bg_counter(_count):
            wwt_widget._on_background_change({"new": wwt_widget.background})
            wwt_widget._on_foreground_change({"new": wwt_widget.foreground})

        background_counter.subscribe(_on_bg_counter)

        def cleanup():
            wwt_widget_container.children = ()
            wwt_widget.close()

        return cleanup

    solara.use_effect(_add_widget, dependencies=[])

    def _on_wwt_ready():
        """
        Set up the WWT widget when it is ready.
        """
        # Apparently, `use_effect` triggers immediately, and then based on
        #  dependencies. So we need to check if the WWT is ready.
        if not show_wwt.value:
            return

        wwt_widget = solara.get_widget(wwt_container).children[0]

        # Update the displayed foreground and background
        wwt_widget.foreground = SDSS
        wwt_widget.background = SDSS

        # Center the field on the location of the table data
        if not show_galaxies:
            _go_to_location(
                wwt_widget, coords=INIT_COORDINATE, fov=1 * u.deg, instant=True
            )

        # Set up the selection callback
        def _on_selection_changed(wwt, updated):
            if "most_recent_source" not in updated:
                return

            source = wwt.most_recent_source
            galaxy = source["layerData"]

            for k in ["ra", "decl"]:
                galaxy[k] = float(galaxy[k])

            fov = min(wwt_widget.get_fov(), GALAXY_FOV)

            _go_to_location(
                wwt_widget,
                coords=SkyCoord(galaxy["ra"], galaxy["decl"], unit=u.deg),
                fov=fov,
            )
            selected.set(galaxy)
            galaxy_selected_callback(galaxy)

        wwt_widget.set_selection_change_callback(_on_selection_changed)

        if on_wwt_ready is not None:
            on_wwt_ready()

    solara.use_effect(_on_wwt_ready, dependencies=[show_wwt.value])

    def _on_show_galaxies():
        """
        Show or hide the galaxies on the WWT widget.
        """
        # WWT must be ready before we can add layers or navigate.
        # If the page is refreshed while show_galaxies is already True, this
        # effect fires on mount before WWT has loaded.  We return early and
        # rely on show_wwt changing to True to re-trigger the effect.
        if not show_wwt.value:
            return

        wwt_widget = solara.get_widget(wwt_container).children[0]

        if current_layer.value is None:
            table = Table(
                {
                    k: [x.dict()[k] for x in LOCAL_API.get_galaxies(local_state)]
                    for k in ["id", "ra", "decl"]
                }
            )

            layer = wwt_widget.layers.add_table_layer(
                frame="Sky",
                table=table,
                lon_att="ra",
                lat_att="decl",
                marker_type="gaussian",
                size_scale=100,
                color="#00FF00",
                marker_scale="screen",
            )

            current_layer.set(layer)

        current_layer.value.opacity = int(show_galaxies)

        if show_galaxies:
            _go_to_location(
                wwt_widget, coords=START_COORDINATES, fov=60 * u.deg, instant=True
            )

    solara.use_effect(_on_show_galaxies, dependencies=[show_galaxies, show_wwt.value])

    def _go_to_location(
        wwt_widget: HubbleWWTWidget,
        coords: SkyCoord,
        fov: u.Quantity,
        instant: Optional[bool] = None,
        motion_counted: bool = True,
    ):
        if instant is None:
            if motion_counted:
                instant = motions_left <= 0
                set_motions_left(motions_left - 1)
            else:
                instant = True

        wwt_widget.center_on_coordinates(
            coords,
            fov=fov,
            instant=instant,
        )

    def _on_reset_view():
        """
        Reset the view of the WWT widget.
        """
        wwt_widget = solara.get_widget(wwt_container).children[0]
        _go_to_location(
            wwt_widget, coords=START_COORDINATES, fov=60 * u.deg, instant=True
        )

    solara.use_effect(_on_reset_view, dependencies=[reset_view.value])

    def _on_refresh_images():
        """
        Refresh the images in the WWT widget.
        """
        wwt_widget = solara.get_widget(wwt_container).children[0]
        wwt_widget.refresh_tile_cache()

    solara.use_effect(_on_refresh_images, dependencies=[refresh_images.value])

    def _update_position(galaxy):
        if galaxy is None:
            return

        coords = SkyCoord(galaxy["ra"] * u.deg, galaxy["decl"] * u.deg, frame="icrs")

        wwt_widget = solara.get_widget(wwt_container).children[0]
        _go_to_location(wwt_widget, coords=coords, fov=GALAXY_FOV, motion_counted=True)

    solara.use_effect(
        lambda: _update_position(selected_galaxy), dependencies=[selected_galaxy]
    )
    solara.use_effect(
        lambda: _update_position(candidate_galaxy), dependencies=[candidate_galaxy]
    )
