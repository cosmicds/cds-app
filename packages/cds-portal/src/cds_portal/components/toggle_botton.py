import solara
from solara.alias import rv
from typing import Callable

@solara.component
def ToggleButton(
    value: solara.Reactive[bool] | bool, 
    disabled: bool = False,
    *args, 
    on_click: Callable[[], None] | None = None, # type: ignore[valid-type]
    on_value: Callable[[bool], None] | None = None, # type: ignore[valid-type]
    label="",
    **kwargs
    ):
    """
    A thin wrapper for rv.Btn that toggles a boolean value
    """
    inner_value = solara.use_reactive(value)
    
    if label != '':
        kwargs["children"] =  kwargs.get("children",[]) + [solara.Text(label)]
    kwargs["disabled"] = disabled
    
    btn = rv.Btn(
        *args, 
        **kwargs)
    def _on_value_changed(*args):
        inner_value.set(not inner_value.value)
        if on_click is not None:
            on_click()
        if on_value is not None:
            on_value(inner_value.value)
    
    solara.v.use_event(btn, "click", _on_value_changed)
    btn