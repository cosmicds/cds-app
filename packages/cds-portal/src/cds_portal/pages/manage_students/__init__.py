import solara
from solara.alias import rv
from ...remote import BASE_API
from datetime import datetime
from ...components.user_generation import CreateStudentAccountsButton


@solara.component
def RemoveStudentDialog(disabled: bool, on_remove_clicked: callable = None):
    active = solara.use_reactive(False)

    with rv.Dialog(
        v_model=active.value,
        on_v_model=active.set,
        v_slots=[
            {
                "name": "activator",
                "variable": "x",
                "children": rv.Btn(
                    v_on="x.on",
                    v_bind="x.attrs",
                    disabled=disabled,
                    text=True,
                    color="error",
                    children=[
                        "Remove",
                    ],
                    elevation=0,
                ),
            }
        ],
        max_width=600,
    ) as dialog:
        with rv.Card(outlined=True, style_=f"border-color: dark-red;"):
            rv.CardTitle(children=["Remove Students"])

            with rv.CardText():
                solara.Text("Are you sure you want to remove the selected student(s)?")

            rv.Divider()

            with rv.CardActions():

                def _remove_button_clicked(*args):
                    on_remove_clicked()
                    active.set(False)

                rv.Spacer()

                solara.Button("Cancel", on_click=lambda: active.set(False), elevation=0)
                solara.Button(
                    "Remove",
                    color="error",
                    on_click=_remove_button_clicked,
                    elevation=0,
                )

    return dialog


@solara.component
def Page():
    selected_rows = solara.use_reactive([])
    data = solara.use_reactive([])
    class_data = solara.use_reactive([])
    search = solara.use_reactive("")

    def _retrieve_students():
        classes_dict = BASE_API.load_educator_classes()
        class_data.set(classes_dict["classes"])
        new_data = []

        for cls in classes_dict["classes"]:
            students = BASE_API.load_students_for_class(cls["id"])

            if len(students) == 0:
                continue

            new_data.extend(
                [
                    {
                        "student_id": student["id"],
                        "class_id": cls["id"],
                        "username": student["username"],
                        "created": datetime.fromisoformat(
                            student["profile_created"].removesuffix("Z")
                        ).strftime("%m/%d/%Y"),
                        "last_visit": datetime.fromisoformat(
                            student["last_visit"].removesuffix("Z")
                        ).strftime("%m/%d/%Y"),
                        "class": cls["name"],
                        "story": "Hubble's Law",
                    }
                    for student in students
                ]
            )

        data.set(new_data)

    solara.use_effect(_retrieve_students, [])

    def _remove_students_from_classes():
        for row in selected_rows.value:
            r = BASE_API.remove_student_from_class(row["student_id"], row["class_id"])

        _retrieve_students()

    with solara.Row():
        with rv.Col(cols=12):
            solara.Div("Manage Students", classes=["display-1", "mb-8"])

            with rv.Card(outlined=True, flat=True):
                with rv.Toolbar(flat=True, dense=True, class_="pa-0"):
                    rv.TextField(
                        v_model=search.value,
                        on_v_model=search.set,
                        label="Search",
                        single_line=True,
                        hide_details=True,
                        filled=True,
                        rounded=True,
                        dense=True,
                        prepend_inner_icon="mdi-magnify",
                    )
                    rv.Divider(vertical=True, class_="ml-4")
                    with rv.ToolbarItems():
                        CreateStudentAccountsButton(class_data.value)
                        RemoveStudentDialog(
                            disabled=len(selected_rows.value) == 0,
                            on_remove_clicked=_remove_students_from_classes,
                        )

                student_table = rv.DataTable(
                    items=data.value,
                    single_select=False,
                    show_select=True,
                    search=search.value,
                    item_key="student_id",
                    v_model=selected_rows.value,
                    on_v_model=selected_rows.set,
                    headers=[
                        {
                            "text": "Username",
                            "align": "start",
                            "sortable": True,
                            "value": "username",
                        },
                        {
                            "text": "Created",
                            "value": "created",
                        },
                        {
                            "text": "Last Visit",
                            "value": "last_visit",
                        },
                        {
                            "text": "Class",
                            "value": "class",
                        },
                        {
                            "text": "Story",
                            "value": "story",
                        },
                        {
                            "text": "Student ID",
                            "value": "student_id",
                            "align": " d-none",
                        },
                        {"text": "Class ID", "value": "class_id", "align": " d-none"},
                    ],
                )
