import solara
from cds_client import CDSClient
from cds_core.components.location_helper.location_helper import LocationHelper
from solara.alias import rv

from cds_portal.components.class_card import ClassCard

from ..components.create_class_dialog import CreateClassDialog
from ..components.overview_header import OverviewHeader
from ..components.story_card import StoryCard
from ..state import get_auth_state, get_portal_state


@solara.component
def EducatorOverview():
    portal_state = get_portal_state()
    active_tab = solara.use_reactive(0)

    search_query = solara.use_reactive("")
    status_filter = solara.use_reactive(1)  # 0=All, 1=Active, 2=Inactive
    sort_by = solara.use_reactive("Date")

    educator = portal_state.educator.value
    verified = educator is not None and educator.verified

    OverviewHeader(role="educator")

    with rv.Container():
        with rv.Row():
            CreateClassDialog(verified)

            filter_field = rv.TextField(
                label="Filter",
                v_model=search_query.value,
                on_v_model=search_query.set,
                outlined=True,
                append_icon="mdi-close-circle" if search_query.value else "",
                dense=True,
            )
            
            solara.v.use_event(
                filter_field,
                "click:append",
                lambda *_: search_query.set(""),
            )
            
            rv.BtnToggle(
                class_="ml-2",
                style_="background: none !important",
                v_model=status_filter.value,
                on_v_model=status_filter.set,
                mandatory=True,
                dense=True,
                children=[
                    rv.Btn(children=["All"], style_="height: 40px"),
                    rv.Btn(children=["Active"], style_="height: 40px"),
                    rv.Btn(children=["Inactive"], style_="height: 40px"),
                ],
            )

            rv.Select(
                label="Sort by",
                v_model=sort_by.value,
                on_v_model=sort_by.set,
                items=["Name", "Date", "Students"],
                outlined=True,
                dense=True,
                hide_details=True,
                class_="ml-2",
                style_="max-width: 160px",
            )

        educator_names = portal_state.class_educator_names.value
        class_progress = portal_state.class_progress.value
        class_sizes = portal_state.class_sizes.value
        status = status_filter.value

        classrooms = [
            filtered_classroom
            for classroom in portal_state.educator_classes.value
            if (
                status == 0
                or (status == 1 and classroom.active)
                or (status == 2 and not classroom.active)
            )
            and (
                filtered_classroom := dict(
                    class_name=classroom.name,
                    class_id=classroom.id,
                    story_name="Hubble's Law",
                    educator_name=educator_names.get(classroom.id, ""),
                    class_code=classroom.code,
                    expected_size=classroom.expected_size,
                    current_size=class_sizes.get(classroom.id),
                    created=classroom.created,
                    active=bool(classroom.active),
                    progress=class_progress.get(classroom.id, 0.0),
                    is_educator=True,
                )
            )
            and any(
                search_query.value.lower() in f"{value}".lower()
                or not search_query.value
                for value in filtered_classroom.values()
            )
        ]

        sort_key = sort_by.value
        if sort_key == "Name":
            classrooms.sort(key=lambda c: (c["class_name"] or "").lower())
        elif sort_key == "Date":
            classrooms.sort(key=lambda c: (c["created"] is None, c["created"]), reverse=True)
        elif sort_key == "Students":
            classrooms.sort(key=lambda c: c["current_size"] or 0, reverse=True)

        for classroom in classrooms:
            code = classroom["class_code"]

            def _deactivate(code=code):
                edu = portal_state.educator.value
                if edu is None:
                    return
                client = CDSClient()
                client.classes.delete(code)
                portal_state.educator_classes = sorted(
                    client.educators.get_classes(edu.id, active_only=False),
                    key=lambda c: (c.created is None, c.created),
                    reverse=True,
                )

            with rv.Row():
                ClassCard(**classroom, on_deactivate=_deactivate)


@solara.component
def StudentOverview():
    portal_state = get_portal_state()

    OverviewHeader(role="student")

    educator_names = portal_state.class_educator_names.value
    class_progress = portal_state.class_progress.value

    classrooms = [
        dict(
            class_name=classroom.name,
            class_id=classroom.id,
            story_name="Hubble's Law",  # This should be retrieved from the story associated with the classroom
            educator_name=educator_names.get(classroom.id, ""),
            class_code=classroom.code,
            expected_size=classroom.expected_size,
            created=classroom.created,
            active=bool(classroom.active),
            progress=class_progress.get(classroom.id, 0.0),
            is_educator=False,
        )
        for classroom in portal_state.student_classes.value
    ]

    with rv.Container():
        for classroom in classrooms:
            with rv.Row():
                ClassCard(**classroom)


@solara.component
def LearnerOverview():
    portal_state = get_portal_state()

    OverviewHeader(role="learner")

    with rv.Container():
        StoryCard(
            story_name=portal_state.story_name.value,
            completed_stages=portal_state.completed_stages.value,
            total_stages=portal_state.total_stages.value,
        )


@solara.component
def Page():
    auth_state = get_auth_state()
    portal_state = get_portal_state()

    authenticated = auth_state.authenticated.value
    loading = portal_state.loading.value

    if authenticated:
        if loading:
            with rv.Container():
                with rv.Row(justify="center", class_="mt-12"):
                    rv.ProgressCircular(indeterminate=True, size=64, color="primary")
        elif portal_state.is_educator.value:
            EducatorOverview()
        elif auth_state.auth_type.value == "student":
            StudentOverview()
        else:
            LearnerOverview()
        return

    LocationHelper(url="/")
