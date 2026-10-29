import os
from pathlib import Path

import solara
from cds_client import CDSClient, EducatorCreationInfo, StudentCreationInfo
from cds_client.auth import hash_user
from cds_client.cookies import verify_student_cookie
from cds_core.components.location_helper.location_helper import LocationHelper
from cds_core.components.theme_toggle import ThemeToggle
from solara.alias import rv
from solara.lab import cookies as solara_cookies, use_dark_effective
from solara_enterprise import auth

from cds_portal.state import get_auth_state, get_portal_state, get_registration_pending

_STORY_NAME = "hubbles_law"
IMG_PATH = Path("static") / "public" / "images"


def _load_story_progress(portal, client, student) -> tuple[int, int]:
    stages = client.stories.get_stages(_STORY_NAME)
    total = len(stages)
    portal.story_name = _STORY_NAME
    portal.total_stages = total
    completed = 0
    if student.id:
        completed = client.stories.count_completed_stages(_STORY_NAME, student.id)
        portal.completed_stages = completed
    return total, completed


def _load_student(portal, client, ref, student):
    portal.is_educator = False
    portal.needs_setup = False
    portal.student = student
    classes = client.students.get_classes(student.id, active_only=False)
    portal.student_classes = classes

    educator_names = {}
    for cls in classes:
        edu = client.educators.get(cls.educator_id)
        if edu is not None:
            educator_names[cls.id] = f"{edu.first_name} {edu.last_name}"
    portal.class_educator_names = educator_names

    total, completed = _load_story_progress(portal, client, student)
    pct = completed / total * 100 if total > 0 else 0.0
    portal.class_progress = {cls.id: pct for cls in classes}


def _load_educator(portal, client, ref, educator):
    portal.is_educator = True
    portal.needs_setup = False
    portal.educator = educator
    classes = sorted(
        client.educators.get_classes(educator.id, active_only=False),
        key=lambda c: (c.created is None, c.created),
        reverse=True,
    )
    portal.educator_classes = classes

    educator_display_name = f"{educator.first_name} {educator.last_name}"
    portal.class_educator_names = {c.id: educator_display_name for c in classes}

    # Load companion student record to get total_stages (avoids a separate get_stages call)
    student = client.students.get(ref)
    if student is not None:
        portal.student = student
        total_stages, _ = _load_story_progress(portal, client, student)
    else:
        total_stages = len(client.stories.get_stages(_STORY_NAME))
        portal.story_name = _STORY_NAME
        portal.total_stages = total_stages

    # Cumulative progress per class: completed stage states / (total_stages × roster size)
    progress = {}
    sizes = {}
    for cls in classes:
        roster_size = client.classes.get_size(cls.id)
        sizes[cls.id] = roster_size
        max_possible = total_stages * roster_size
        if max_possible > 0:
            completed = client.stories.count_class_stage_states(_STORY_NAME, cls.id)
            progress[cls.id] = completed / max_possible * 100
        else:
            progress[cls.id] = 0.0
    portal.class_progress = progress
    portal.class_sizes = sizes


def _create_oauth_account(portal, client, ref):
    pending = get_registration_pending()
    role = pending.role.value
    hidden_code = os.environ.get("CDS_HIDDEN_CLASS_CODE", "")

    if role == "learner":
        client.students.create(
            StudentCreationInfo(username=ref, password="", classroom_code=hidden_code)
        )
        pending.role = None
        student = client.students.get(ref)
        if student is not None:
            _load_student(portal, client, ref, student)

    elif role == "educator":
        edu_data = pending.educator_data.value or {}
        client.educators.create(
            EducatorCreationInfo(
                username=ref,
                password="",
                first_name=edu_data.get("first_name", ""),
                last_name=edu_data.get("last_name", ""),
                email=edu_data.get("email", ""),
                institution=edu_data.get("institution") or None,
            )
        )
        client.students.create(
            StudentCreationInfo(username=ref, password="", classroom_code=hidden_code)
        )
        pending.role = None
        pending.educator_data = None
        educator = client.educators.get(ref)
        if educator is not None:
            _load_educator(portal, client, ref, educator)

    else:
        portal.needs_setup = True


@solara.component
def Layout(children=[]):
    route_current, routes = solara.use_route()
    show_menu = solara.use_reactive(False)
    dark_effective = use_dark_effective()

    # Still need to watch auth.user to detect the OAuth callback
    oauth_user = auth.user.use_value()
    all_cookies = solara_cookies.use_value()

    auth_state = get_auth_state()
    portal_state = get_portal_state()

    authenticated = auth_state.authenticated.value
    user_ref = auth_state.user_ref.value

    def _sync_student_cookie():
        """Populate AuthState from the cds_student cookie when no OAuth session exists."""
        if auth.user.value is not None:
            return
        cookie_val = all_cookies.get("cds_student", "")
        if not cookie_val:
            return
        username = verify_student_cookie(cookie_val)
        if username is None:
            return
        a = get_auth_state()
        if a.authenticated.value:
            return
        a.authenticated = True
        a.auth_type = "student"
        a.user_ref = username
        a.display_name = username

    def _sync_oauth():
        """Translate auth.user (OAuth) into AuthState when an OAuth login completes."""
        if auth.user.value is None:
            return
        userinfo = auth.user.value.get("userinfo", {})
        ref_input = userinfo.get("cds/email") or userinfo.get("cds/name", "")
        if not ref_input:
            return
        a = get_auth_state()
        a.authenticated = True
        a.auth_type = "oauth"
        a.user_ref = hash_user(ref_input)
        a.display_name = userinfo.get("cds/name", "")
        a.picture = userinfo.get("cds/picture", "")

    def _load_portal_state():
        """Load DB records into PortalState once AuthState is populated."""
        a = get_auth_state()
        if not a.authenticated.value:
            return

        portal = get_portal_state()
        portal.loading = True

        ref = a.user_ref.value
        auth_type = a.auth_type.value
        client = CDSClient()

        if auth_type == "oauth":
            # Educators also have a companion student record — check educators FIRST
            # so they are never misidentified as plain students.
            educator = client.educators.get(ref)
            if educator is not None:
                _load_educator(portal, client, ref, educator)
            else:
                student = client.students.get(ref)
                if student is not None:
                    _load_student(portal, client, ref, student)
                else:
                    _create_oauth_account(portal, client, ref)

        elif auth_type == "student":
            student = client.students.get(ref)
            if student is not None:
                _load_student(portal, client, ref, student)

        portal.loading = False

    # Hooks must be called unconditionally before any early returns
    solara.use_memo(_sync_student_cookie, dependencies=[all_cookies])
    solara.use_memo(_sync_oauth, dependencies=[oauth_user])
    solara.use_memo(_load_portal_state, dependencies=[authenticated, user_ref])

    loading = portal_state.loading.value
    display_name = auth_state.display_name.value or ""
    picture = auth_state.picture.value or ""

    with rv.App():
        solara.Title("Cosmic Data Stories | PORTAL")

        with rv.AppBar(app=True):
            with rv.Container(class_="pa-0 fill-height"):
                rv.Avatar(
                    children=[rv.Img(src=str(IMG_PATH / "logo.webp"))],
                    tile=True,
                    width=56,
                )
                rv.ToolbarTitle(children=["CDS | PORTAL"], class_="ml-4")

                rv.Spacer()

                ThemeToggle(enable_auto=False, default_theme="dark")

                if authenticated:
                    with rv.Menu(
                        bottom=True,
                        left=True,
                        offset_y=True,
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
                                                [rv.Img(src=picture)]
                                                if picture
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
                        with rv.Card(class_="pa-0"):
                            with rv.List(dense=True):
                                with rv.ListItem(dense=True, link=True, href="/"):
                                    with rv.ListItemIcon():
                                        rv.Icon(children=["mdi-view-dashboard"])
                                    with rv.ListItemContent():
                                        rv.ListItemTitle(children=["Overview"])

                                with rv.ListItem(
                                    dense=True,
                                    link=True,
                                    href=(
                                        "/student-logout"
                                        if auth_state.auth_type.value == "student"
                                        else auth.get_logout_url("/")
                                    ),
                                ):
                                    with rv.ListItemIcon():
                                        rv.Icon(children=["mdi-logout"])
                                    with rv.ListItemContent():
                                        rv.ListItemTitle(children=["Logout"])

        with rv.Content(children=children):
            pass

        with rv.Footer(app=False, padless=True, class_="mt-4"):
            border = "border-top: 1px solid #424242" if dark_effective else ""
            with rv.Container(fluid=False, style_=border):
                with rv.Row(justify="space-between"):
                    with rv.Col(cols=12, md=6):
                        # rv.Sheet(class_="pa-12", color="grey lighten-2")
                        solara.Markdown(
                            "## Cosmic Data Stories", style="margin-top: 0px; padding-top: 0px"
                        )
                        solara.Markdown(
                            "Center for Astrophysics Harvard | Smithsonian, 60 Garden Street, Cambridge, MA 02138",
                            style="font-size: 1rem; opacity: 0.75",
                        )
                        solara.Markdown(
                            "The material contained on this website is based upon work supported "
                            "by NASA under award No. 80NSSC21M0002 Any opinions, findings, and "
                            "conclusions or recommendations expressed in this material are those "
                            "of the author(s) and do not necessarily reflect the views of the "
                            "National Aeronautics and Space Administration.",
                            style="font-size: 0.8rem",
                        )
                        solara.Markdown(
                            "© 2026 The President and Fellows of Harvard College",
                            style="font-size: 0.8rem; opacity: 0.6;",
                        )
                    with rv.Col(cols=12, md=3):
                        # rv.Sheet(class_="pa-12", color="grey lighten-2")
                        with rv.List():
                            with rv.ListItem():
                                with rv.ListItemContent():
                                    rv.ListItemTitle(children=["Documentation"])
                            with rv.ListItem():
                                with rv.ListItemContent():
                                    rv.ListItemTitle(children=["FAQ & Help"])
                            with rv.ListItem():
                                with rv.ListItemContent():
                                    rv.ListItemTitle(children=["Contact Us"])
                            with rv.ListItem():
                                with rv.ListItemContent():
                                    rv.ListItemTitle(children=["Privacy Policy"])
                            with rv.ListItem():
                                with rv.ListItemContent():
                                    rv.ListItemTitle(children=["Terms of Service"])

                    with rv.Col(cols=12, md=3):
                        with rv.Sheet(class_="pa-4 mb-4", color="grey darken-2"):
                            rv.Img(
                                src=str(IMG_PATH / "cfa_theme_logo_black.webp"),
                                contain=True,
                                height=50,
                            )
                        with rv.Sheet(class_="pa-0", color="white"):
                            rv.Img(
                                src=str(IMG_PATH / "nasa-granteeinsignia-rgb.webp"),
                                contain=True,
                                height="100",
                            )
