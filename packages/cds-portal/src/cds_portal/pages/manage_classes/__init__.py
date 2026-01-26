from collections import defaultdict
from datetime import datetime
from typing import Callable, Optional

import solara
from solara.alias import rv
from solara.server import settings


from cds_portal.components.input import IntegerInput
from cds_portal.components.toggle_botton import ToggleButton

from ...remote import BASE_API


# If we want to remove more characters in the future
# (or replace more with underscores)
# switch to using re.sub
def format_story_name(name: str):
    return name.lower().replace("'", "").replace(" ", "_")


@solara.component
def CreateClassDialog(on_create_clicked: callable = None):
    active, set_active = solara.use_state(False)  #
    text, set_text = solara.use_state("")
    stories, set_stories = solara.use_state("")
    expected_size, set_expected_size = solara.use_state(20)
    asynchronous, set_asynchronous = solara.use_state(False)
    pad, set_pad = solara.use_state(True)
    expected_size_error = solara.use_reactive(False)

    with rv.Dialog(
        v_model=active,
        on_v_model=set_active,
        v_slots=[
            {
                "name": "activator",
                "variable": "x",
                "children": rv.Btn(
                    v_on="x.on",
                    v_bind="x.attrs",
                    children=["Add Class"],
                    elevation=0,
                    color="success",
                    class_="ma-2 black--text",
                ),
            }
        ],
        max_width=600,
    ) as dialog:
        with rv.Card(outlined=True):
            rv.CardTitle(children=["Create a New Class"])

            with rv.CardText():
                rv.TextField(
                    label="Class name",
                    outlined=True,
                    required=True,
                    hide_details="auto",
                    v_model=text,
                    on_v_model=set_text,
                )

                rv.Select(
                    v_model=stories,
                    outlined=True,
                    on_v_model=set_stories,
                    class_="pt-2",
                    hide_details="auto",
                    label="Data Story",
                    items=["Hubble's Law"],
                    multiple=False,
                )

                IntegerInput(
                    label="Expected size",
                    value=expected_size,
                    on_value=set_expected_size,
                    on_error_change=expected_size_error.set,
                    continuous_update=True,
                    outlined=True,
                    hide_details="auto",
                    classes=["pt-2"],
                )

                solara.Checkbox(
                    label="Asynchronous class",
                    value=asynchronous,
                    on_value=set_asynchronous,
                )

                solara.Text("""
                    Would you like to pad your class's data with data from previous students?
                    This will allow your students to dive directly into examining data in Stages 4 and 5 without waiting,
                    but means that they will see data from students other than just their classmates
                """)
                solara.Checkbox(
                    label="Pad class data",
                    value=pad,
                    on_value=set_pad,
                )

            rv.Divider()

            with rv.CardActions():

                @solara.lab.computed
                def create_button_disabled():
                    return expected_size_error.value or (not (text and stories))

                def _add_button_clicked(*args):
                    on_create_clicked(
                        {
                            "name": f"{text}",
                            "stories": f"{', '.join(stories)}",
                            "expected_size": expected_size,
                            "asynchronous": asynchronous,
                            "story_name": format_story_name(stories),
                            "pad": pad,
                        }
                    )
                    set_active(False)

                rv.Spacer()

                solara.Button("Cancel", on_click=lambda: set_active(False), elevation=0)
                solara.Button(
                    "Create",
                    color="accent",
                    on_click=_add_button_clicked,
                    elevation=0,
                    disabled=create_button_disabled.value,
                    class_="ma-2 black--text",
                )

    return dialog


@solara.component
def DeleteClassDialog(disabled: bool, on_delete_clicked: callable = None):
    active, set_active = solara.use_state(False)

    with rv.Dialog(
        v_model=active,
        on_v_model=set_active,
        v_slots=[
            {
                "name": "activator",
                "variable": "x",
                "children": rv.Btn(
                    v_on="x.on",
                    v_bind="x.attrs",
                    color="error",
                    disabled=disabled,
                    children=[
                        "Delete",
                    ],
                    elevation=0,
                    class_="ma-2",
                ),
            }
        ],
        max_width=600,
    ) as dialog:
        with rv.Card(outlined=True, style_=f"border-color: dark-red;"):
            rv.CardTitle(children=["Delete Class"])

            with rv.CardText():
                solara.Div("Are you sure you want to delete the selected class(es)?")

            rv.Divider()

            with rv.CardActions():

                def _delete_button_clicked(*args):
                    on_delete_clicked()
                    set_active(False)

                rv.Spacer()

                solara.Button("Cancel", on_click=lambda: set_active(False), elevation=0)
                solara.Button(
                    "Delete",
                    color="error",
                    on_click=_delete_button_clicked,
                    elevation=0,
                    class_="ma-2",
                )

    return dialog


@solara.component
def ClassActionsDialog(disabled: bool,
                       class_data: list[dict],
                       on_active_changed: Optional[Callable] = None):
    active, set_active = solara.use_state(False)
    message, set_message = solara.use_state("")
    message_color, set_message_color = solara.use_state("")

    with rv.Dialog(
        v_model=active,
        on_v_model=set_active,
        v_slots=[
            {
                "name": "activator",
                "variable": "x",
                "children": rv.Btn(
                    v_on="x.on",
                    v_bind="x.attrs",
                    disabled=disabled,
                    children=["Modify class"],
                    elevation=0,
                    color="accent",
                    class_="ma-2 black--text",
                )
            }
        ],
        max_width=600,
    ):

        def _update_snackbar(message: str, color: str):
            set_message_color(color)
            set_message(message)

        def _reset_snackbar():
            set_message("")

        def close_dialog():
            set_active(False)
            _reset_snackbar()

        classes_by_story = defaultdict(list)
        for data in class_data:
            classes_by_story[data["story"]].append(data)

        with rv.Card(outlined=True):
            rv.CardTitle(children=["Modify Class"])

            with rv.CardText():
                solara.Div("From this dialog you can make any necessary changes to the selected classes")

            def _on_active_switched(active: bool):
                for data in class_data:
                    BASE_API.set_class_active(data["id"], "hubbles_law", active)

                if on_active_changed is not None:
                    on_active_changed(class_data, active)

            with rv.Container():
                with rv.CardText():
                    single_class = len(class_data) == 1
                    classes_string = "class" if single_class else "classes"
                    is_are_string = "is" if single_class else "are"
                    solara.Text(f"Set whether or not the selected {classes_string} {is_are_string} active")
                with solara.Row():
                    any_active = any(BASE_API.get_class_active(data["id"], "hubbles_law") for data in class_data)
                    solara.Switch(label="Set active", value=any_active, on_value=_on_active_switched)
                    rv.Alert(children=[f"This will affect {len(class_data)} {classes_string}"],
                             color="accent",
                             outlined=True,
                             dense=True)

            if "Hubble's Law" in classes_by_story:

                hubble_classes = classes_by_story["Hubble's Law"]

                override_statuses = [BASE_API.get_hubble_waiting_room_override(data["id"])["override_status"] for data in hubble_classes]
                all_overridden = all(override_statuses)

                def _on_override_button_pressed(*args):
                    failures = []
                    for data in hubble_classes:
                        class_id = data["id"]
                        response = BASE_API.set_hubble_waiting_room_override(class_id, True)
                        success = response.status_code in (200, 201)
                        if not success:
                            failures.append(class_id)

                    relevant_ids = failures if failures else [data["id"] for data in hubble_classes]
                    classes_string = "class" if len(relevant_ids) == 1 else "classes"
                    ids_string = ", ".join(str(cid) for cid in relevant_ids)
                    message = f"There was an error updating the waiting room status for {classes_string} {ids_string}" if failures else \
                              f"Updated waiting room status for {classes_string} {ids_string}"
                    color = "error" if failures else "success"

                    _update_snackbar(message=message, color=color)

                with rv.Container():
                    with rv.CardText():
                        solara.Text("Set the small class override for the selected classes. If a class already has the override set, there will be no effect.")
                    with solara.Row():
                        no_override_count = len(hubble_classes) - sum(override_statuses)
                        no_override_classes = "class" if no_override_count == 1 else "classes"
                        solara.Button(label="Set override",
                                      on_click=_on_override_button_pressed,
                                      disabled=all_overridden)
                        rv.Alert(children=[f"This will affect {no_override_count} {no_override_classes}"],
                                 color="accent",
                                 outlined=True,
                                 dense=True)

                rv.Spacer()

                with rv.CardActions():
                    solara.Button("Close", on_click=close_dialog, elevation=0, color="info")

        rv.Snackbar(v_model=bool(message),
                    on_v_model=lambda *args: _reset_snackbar(),
                    color=message_color,
                    timeout=5000,
                    children=[message])



def ChangeClassActivation(disabled: bool,
                       class_data: list[dict],
                       on_active_changed: Optional[Callable] = None,
                       on_mixed_active_changed: Optional[Callable] = None):

    classes_by_story = defaultdict(list)
    for data in class_data:
        classes_by_story[data["story"]].append(data)

    _active = [BASE_API.get_class_active(data["id"], "hubbles_law") for data in class_data]
    any_active = any(_active)
    all_active = all(_active)
    mixed_active = not (all_active or not any_active) 

    if on_mixed_active_changed is not None:
        on_mixed_active_changed(mixed_active)

    def _on_active_switched(active: bool):
        for data in class_data:
            BASE_API.set_class_active(data["id"], "hubbles_law", active)

        if on_active_changed is not None:
            on_active_changed(class_data, active)
    
    single_class = len(class_data) == 1
    classes_string = "class" if single_class else "classes"
    is_are_string = "is" if single_class else "are"
    label = ""
    if disabled or mixed_active:
        label = "(De)Activate "+ classes_string
    elif any_active:
        label = "Deactivate "+ classes_string
    else:
        label = "Activate "+ classes_string
        
    # two rv.Btns on for each option
    with solara.Div(classes=["d-flex","align-center"],style={"color": "var(--black--text)", "border-radius": "5px"}):
        solara.Button(
            disabled=disabled,
            label="Activate",
            color="accent",
            on_click=lambda: _on_active_switched(True),
            class_="my-1 mx-2 black--text",
        )
        solara.Button(
            disabled=disabled,
            label="Deactivate",
            color="accent",
            on_click=lambda: _on_active_switched(False),
            class_="my-1 mx-2 black--text",
        )
    

        
    # solara.Switch(label="Set active", value=any_active, on_value=_on_active_switched)
    # ToggleButton(
    #     label=label,
    #     value=any_active,
    #     on_value=_on_active_switched,
    #     color="accent",
    #     disabled=disabled,
    #     class_="ma-2 black--text",
    # )



@solara.component
def Page():
    data = solara.use_reactive([])
    selected_rows = solara.use_reactive([])
    retrieve = solara.use_reactive(0)
    mixed_active, set_mixed_active = solara.use_state(False)

    def _retrieve_classes():
        classes_dict = BASE_API.load_educator_classes()

        new_classes = [
            {
                "name": cls["name"],
                "date": datetime.fromisoformat(cls["created"].removesuffix("Z")).strftime("%m/%d/%Y"),
                "story": "Hubble's Law",
                "code": cls["code"],
                "id": cls["id"],
                "expected_size": cls["expected_size"],
                "small_class": cls["small_class"],
                "asynchronous": cls["asynchronous"],
                "active": BASE_API.get_class_active(cls["id"], "hubbles_law"),
            }
            for cls in classes_dict["classes"]
        ]

        data.set(new_classes)

    solara.use_effect(_retrieve_classes, [retrieve.value])

    def _create_class_callback(class_info):
        BASE_API.create_new_class(class_info)
        _retrieve_classes()

    def _delete_class_callback():
        for row in selected_rows.value:
            BASE_API.delete_class(row["code"])
        _retrieve_classes()

    with solara.Row(classes=["fill-height"]):
        with rv.Col(cols=12):
            with rv.Row(class_="pa-0 mb-0 mx-0"):
                solara.Text("Manage Classes", classes=["display-1"])

            with rv.Row(class_="class_buttons mb-2 mx-0"):

                # ClassActionsDialog(
                #     disabled = len(selected_rows.value) == 0, 
                #     class_data = selected_rows.value,
                #     on_active_changed=lambda *args: retrieve.set(retrieve.value + 1)
                # )
                solara.Button(
                    "Educator Preview",
                    text=False,
                    color="success",
                    disabled=False,
                    href=f"{settings.main.base_url}hubbles-law",
                    target="_blank",
                    class_="ma-2 black--text",
                )  
                
                CreateClassDialog(_create_class_callback)

                rv.Spacer()
                
                if len(data.value) > 0:
                    ChangeClassActivation(
                        disabled = len(selected_rows.value) == 0, 
                        class_data = selected_rows.value,
                        on_active_changed=lambda *args: retrieve.set(retrieve.value + 1),
                        on_mixed_active_changed=set_mixed_active,
                    )      
                
                rv.Spacer()
                
                if len(data.value) > 0:
                    solara.Button(
                        "Dashboard",
                        color="success",
                        href=(
                            f"/educator-dashboard?id={selected_rows.value[0]['id']}"
                            if len(selected_rows.value) == 1
                            else "/educator-dashboard"
                        ),
                        elevation=0,
                        disabled=len(selected_rows.value) != 1,
                        class_="ma-2 black--text",
                    )    

                # DeleteClassDialog(
                #             len(selected_rows.value) == 0, _delete_class_callback
                #   

                
                

            with rv.Card(outlined=True, flat=True):

                rv.DataTable(
                    items=data.value,
                    single_select=False,
                    show_select=True,
                    v_model=selected_rows.value,
                    on_v_model=selected_rows.set,
                    headers=[
                        {
                            "text": "Name",
                            "align": "start",
                            "sortable": True,
                            "value": "name",
                        },
                        {"text": "Date", "value": "date"},
                        {"text": "Story", "value": "story"},
                        {"text": "Code", "value": "code"},
                        {"text": "ID", "value": "id", "align": "d-none"},
                        # {"text": "Expected size", "value": "expected_size"},
                        {"text": "Class Active", "value": "active"},
                        # {"text": "Asynchronous", "value": "asynchronous"},
                    ],
                    hide_default_footer=True,
                )
