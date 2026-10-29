import solara
from solara.alias import rv


@solara.component
def ClassesTable(classes, show_code=True):
    headers = [{"text": "Name", "value": "name", "sortable": True}]
    if show_code:
        headers.append({"text": "Code", "value": "code", "sortable": False})
    headers += [
        {"text": "Expected size", "value": "expected_size", "sortable": True},
        {"text": "Created", "value": "created", "sortable": True},
    ]

    items = [
        {
            "name": c.name,
            "code": c.code,
            "expected_size": c.expected_size,
            "created": c.created.strftime("%Y-%m-%d") if c.created else "",
        }
        for c in classes
    ]

    rv.DataTable(
        headers=headers,
        items=items,
        hide_default_footer=len(items) <= 10,
        no_data_text="No classes yet.",
    )
