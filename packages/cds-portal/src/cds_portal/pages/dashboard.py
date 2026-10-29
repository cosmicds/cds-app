import solara
from cds_core.components.location_helper.location_helper import LocationHelper
from cds_dashboard.educator_dashboard import EducatorDashboard
from solara.alias import rv

from ..state import get_auth_state, get_portal_state


@solara.component
def Page():
    auth_state = get_auth_state()
    portal_state = get_portal_state()
    router = solara.use_router()

    authenticated = auth_state.authenticated.value
    loading = portal_state.loading.value
    is_educator = portal_state.is_educator.value

    if not authenticated:
        LocationHelper(url="/")
        return

    if loading:
        with rv.Container():
            with rv.Row(justify="center", class_="mt-12"):
                rv.ProgressCircular(indeterminate=True, size=64, color="primary")
        return

    if not is_educator:
        LocationHelper(url="/overview")
        return

    url_params = {}
    if router.search:
        url_params = {
            part.split("=")[0]: part.split("=")[1]
            for part in router.search.split("&")
            if "=" in part
        }

    classes = portal_state.educator_classes.value
    class_info_list = [
        {"id": cls.id, "name": cls.name, "code": cls.code}
        for cls in classes
    ]
    educator_class_ids = {str(cls.id) for cls in classes}

    if url_params.get("id") not in educator_class_ids:
        with rv.Container():
            solara.Markdown("You do not have access to this class.")
        return

    with rv.Container():
        EducatorDashboard(class_info_list=class_info_list)
