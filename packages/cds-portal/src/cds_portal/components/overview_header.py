import solara
from solara.alias import rv

from cds_portal.state import get_auth_state, get_portal_state


@solara.component
def OverviewHeader(role: str):
    auth_state = get_auth_state()
    portal_state = get_portal_state()
    display_name = auth_state.display_name.value or auth_state.user_ref.value or ""
    educator = portal_state.educator.value

    with rv.Container(class_="pb-0"):
        with rv.Row(align="center", class_="pb-0"):
            with rv.Col():
                solara.Text(
                    f"Welcome, {display_name}",
                    style="font-size: 1.5rem; font-weight: 500;",
                )
            with rv.Col(cols="auto"):
                rv.Chip(children=[role.title()], color="primary", outlined=True)
                if role == "educator" and educator is not None:
                    if not educator.verified:
                        rv.Chip(
                            children=["Verification Pending"],
                            color="warning",
                            outlined=True,
                            class_="ml-2",
                        )
                    else:
                        rv.Chip(
                            children=["Verified"],
                            color="success",
                            outlined=True,
                            class_="ml-2",
                        )
