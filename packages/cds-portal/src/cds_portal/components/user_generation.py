import solara
from solara.alias import rv
from solara.lab import computed

from cds_usergen.pages import CreateStudentsForClass

def CreateStudentAccountsDialog(classes):
    selected_class_code = solara.use_reactive(None)
    selected_class = solara.use_reactive({})
    class_options = [{"text": c.get("name", ""), "value": c.get("code", "")} for c in classes]

    @computed
    def expected_size():
        if selected_class_code.value:
            selected_class.value = next(c for c in classes if c['code'] == selected_class_code.value)
            if selected_class.value:
                return selected_class.value['expected_size']
        return None

    rv.Select(
        items=class_options,
        v_model=selected_class_code.value,
        on_v_model=selected_class_code.set,
        label="Class",
        hide_details=True,
    )
    if selected_class_code.value:
        # solara.Text(f"{selected_class.value}")
        CreateStudentsForClass(selected_class_code, howManyValue=expected_size)



@solara.component
def CreateStudentAccountsButton(classes):
    
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
                    color="black",
                    children=["Create accounts for students"],
                    elevation=0,
                ),
            }
        ],
        max_width=600,
    ) as dialog:
        with rv.Card(outlined=True,):
            rv.CardTitle(children=["Create student accounts for class"])
            with rv.CardText():
                CreateStudentAccountsDialog(classes)