from pathlib import Path

import ipyvuetify as v
import solara
from solara.alias import rv
from solara_enterprise import auth
import httpx
from solara.lab import Ref

from .state import GLOBAL_STATE, UserType
from .remote import BASE_API
from .components.hero import Hero
from .components.setup_dialog import UserTypeSetup
from cds_core.components.theme_toggle import ThemeToggle


IMG_PATH = Path("static") / "public" / "images"


@solara.component
def Layout(children=[]):
    router = solara.use_router()
    route_current, routes = solara.use_route()
    show_menu = solara.use_reactive(False)
    setup_finished = Ref(GLOBAL_STATE.fields.initial_setup_finished)

    def _check_user_status():
        if (info := BASE_API.educator_info) is not None:
            Ref(GLOBAL_STATE.fields.user.user_type).set(UserType.educator)
            Ref(GLOBAL_STATE.fields.user.id).set(info["id"])
        elif (info := BASE_API.student_info) is not None:
            Ref(GLOBAL_STATE.fields.user.user_type).set(UserType.student)
            Ref(GLOBAL_STATE.fields.user.id).set(info["id"])

    solara.use_effect(_check_user_status, [setup_finished.value])

    @solara.lab.computed
    def user_typename():
        user = Ref(GLOBAL_STATE.fields.user)
        if user.value.is_educator:
            return "Educator"
        elif user.value.is_student:
            return "Student"
        else:
            return ""

    with rv.App(dark=True) as main:
        solara.Title("Cosmic Data Stories")

        with rv.AppBar(elevate_on_scroll=True, app=True):

            with rv.Container(class_="py-0 fill-height"):
                with solara.Link(solara.resolve_path("/")):
                    with rv.Avatar(class_="mr-8", width="60", tile=True):
                        rv.Img(
                            src=str(
                                IMG_PATH
                                / "cosmicds_logo_transparent_for_dark_backgrounds.webp"
                            ),
                        )

                solara.Button(
                    "Data Stories",
                    text=True,
                    on_click=lambda: router.push("/data_stories"),
                )
                solara.Button(
                    children=["About"],
                    text=True,
                    on_click=lambda: router.push("/about"),
                )
                solara.Button(
                    children=["Team"], text=True, on_click=lambda: router.push("/team")
                )
                solara.Button(
                    children=["Contact"],
                    text=True,
                    on_click=lambda: router.push("/contact"),
                )
                # solara.Button(children=["Privacy"], text=True)
                # solara.Button(children=["Digital Accessibility"], text=True)

                rv.Spacer()

                if not Ref(GLOBAL_STATE.fields.user.is_validated).value:
                    solara.Button(
                        "Sign in", href=auth.get_login_url(), text=True, outlined=True
                    )
                else:
                    if not (BASE_API.student_info or BASE_API.educator_info):
                        UserTypeSetup()

                    ThemeToggle(
                        on_icon="mdi-brightness-4",  # dark mode icon
                        off_icon="mdi-brightness-4",  # light mode icon
                        enable_auto=False,
                        default_theme="dark",
                        enforce_default=True,
                    )
                    # rv.Btn(icon=True, children=[rv.Icon(children=["mdi-bell"])])

                    with rv.Menu(
                        bottom=True,
                        left=True,
                        offset_y=True,
                        offset_x=False,
                        v_model=show_menu.value,
                        on_v_model=show_menu.set,
                        v_slots=[
                            {
                                "name": "activator",
                                "variable": "x",
                                "children": rv.Btn(
                                    icon=True,
                                    class_="ml-2",
                                    children=[
                                        rv.Avatar(
                                            children=(
                                                [
                                                    rv.Img(
                                                        src=f"{auth.user.value['userinfo'].get('cds/picture', '')}"
                                                    )
                                                ]
                                                if auth.user.value["userinfo"].get(
                                                    "cds/picture"
                                                )
                                                is not None
                                                else [
                                                    rv.Icon(
                                                        children=["mdi-account-circle"]
                                                    )
                                                ]
                                            ),
                                        )
                                    ],
                                    text=True,
                                    outlined=True,
                                    v_on="x.on",
                                ),
                            }
                        ],
                    ):
                        with rv.List(dense=True, nav=True, max_width=300):
                            user_id = Ref(GLOBAL_STATE.fields.user.id)
                            user_menu_list = []

                            if user_typename.value == "Educator":
                                user_menu_list.append(
                                    rv.ListItemSubtitle(
                                        children=[
                                            f"{auth.user.value['userinfo'].get('cds/email', '')}"
                                        ]
                                    )
                                )
                            user_menu_list.append(
                                rv.ListItemSubtitle(
                                    children=[
                                        f"{user_typename.value} ID: {user_id.value}"
                                    ]
                                )
                            )
                            with rv.ListItem():
                                rv.ListItemAvatar(
                                    children=[
                                        rv.Img(
                                            src=f"{auth.user.value['userinfo'].get('cds/picture', '')}"
                                        )
                                    ]
                                ),
                                rv.ListItemContent(
                                    children=user_menu_list,
                                )

                            rv.Divider(class_="pb-1")

                            if (
                                Ref(GLOBAL_STATE.fields.user.user_type).value
                                == UserType.student
                            ):
                                with rv.ListItem(link=True) as classes_item:
                                    with rv.ListItemIcon():
                                        rv.Icon(children=["mdi-account"])

                                    rv.ListItemTitle(children=["My Classes"])

                                solara.v.use_event(
                                    classes_item,
                                    "click",
                                    lambda *args: router.push("/student_classes"),
                                )
                            elif (
                                Ref(GLOBAL_STATE.fields.user.user_type).value
                                == UserType.educator
                            ):
                                with rv.ListItem(link=True) as classes_item:
                                    with rv.ListItemIcon():
                                        rv.Icon(children=["mdi-book"])

                                    rv.ListItemTitle(children=["Manage Classes"])

                                solara.v.use_event(
                                    classes_item,
                                    "click",
                                    lambda *args: router.push("/manage_classes"),
                                )
                                with rv.ListItem(link=True) as classes_item:
                                    with rv.ListItemIcon():
                                        rv.Icon(children=["mdi-account-group"])

                                    rv.ListItemTitle(children=["Manage Students"])

                                solara.v.use_event(
                                    classes_item,
                                    "click",
                                    lambda *args: router.push("/manage_students"),
                                )

                            # with rv.ListItem(link=True):
                            #     with rv.ListItemIcon():
                            #         rv.Icon(children=["mdi-settings"])

                            #     rv.ListItemTitle(children=["Settings"])

                            rv.Divider(class_="pb-1")

                            solara.Button(
                                "Logout",
                                style="width:100%",
                                icon_name="mdi-logout",
                                color="info",
                                flat=True,
                                text=False,
                                on_click=lambda: router.push("/"),
                                href=auth.get_logout_url("/"),
                            )
                    if user_typename.value == "Student" and user_id.value is not None:
                        solara.Text(
                            f"{user_typename.value} ID: {user_id.value}",
                            classes=["ml-4"],
                        )

        with rv.Content():
            if route_current.path == "/":
                Hero()

            with rv.Container(
                children=children,
                # class_="fill-height",
                # style_="max-width: 1200px",
            ):
                pass

        with rv.Footer(
            app=False,
            padless=True,
            style_="background-color: #272727 !important; color: white !important;",
        ):
            with rv.Container(style="max-width: 1200px"):

                with rv.Row():
                    with rv.Col(cols=4):
                        solara.Text("Cosmic Data Stories", classes=["title"])
                        solara.HTML(
                            unsafe_innerHTML="""
                                Center for Astrophysics Harvard | Smithsonian<br/>
                                60 Garden Street<br/>
                                Cambridge, MA  02138
                            """,
                            classes=["text-h6"],
                        )

                    with rv.Col(cols=4):
                        rv.Img(
                            src=str(
                                IMG_PATH / "NASA_Partner_color_300_no_outline.webp"
                            ),
                            contain=True,
                            height="100",
                        )

                    with rv.Col(cols=4):
                        rv.Img(
                            src=str(IMG_PATH / "cfa_theme_logo_black.webp"),
                            contain=True,
                            height=50,
                        )

                with rv.Row():
                    with rv.Col(class_="text-center", cols=10, offset=1):
                        solara.Div(
                            children=[
                                "The material contained on this website is based upon work supported by NASA under "
                                "award No. 80NSSC21M0002 Any opinions, findings, and conclusions or recommendations "
                                "expressed in this material are those of the author(s) and do not necessarily reflect "
                                "the views of the National Aeronautics and Space Administration."
                            ],
                            classes=["caption mb-4"],
                        )
                        solara.Text(
                            "Copyright © 2025 The President and Fellows of Harvard College",
                        )

    return main
