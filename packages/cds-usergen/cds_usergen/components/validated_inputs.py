import solara
from solara.alias import rv
from solara.lab import use_task, Task, computed
from typing import Callable

MAX_LENGTH = 15

@solara.component
def ValidatedTextInput(
    max_length: int = MAX_LENGTH,
    validator: Callable = None, 
    error_message: Callable = None, 
    continuous_update = False,
    **kwargs,
    ):

    value = solara.use_reactive(kwargs.pop('value'))
    innerValue = solara.use_reactive('')
    
    
    @computed
    def is_valid():
        if validator is not None:
            return validator(innerValue.value)
        return len(innerValue.value) <= MAX_LENGTH
    
    @computed
    def error():
        if is_valid.value:
            return None
        if error_message is not None:
            return error_message(innerValue.value)
        return f"Length: ({len(innerValue.value)}) is longer than max: {MAX_LENGTH}"

    def set_value():
        if is_valid.value:
            value.set(innerValue.value)
    
    solara.use_effect(set_value, [innerValue.value])

    solara.InputText(
        value = innerValue,
        continuous_update = True,
        # error=error.value,
        **kwargs
    )
    
    if error.value:
        solara.Error(label=error.value, dense=True, text=True, outlined=False)


@solara.component
def ValidatedInputInt(
    max: int = 100,
    min: int = 0,
    validator: Callable = None,
    error_message: Callable = None,
    **kwargs,
):

    value = solara.use_reactive(kwargs.pop('value'))
    innerValue = solara.use_reactive(value.value)

    @computed
    def is_valid():
        if validator is not None:
            return validator(innerValue.value)
        return innerValue.value < max

    @computed
    def error():
        if is_valid.value:
            return ""
        if error_message is not None:
            return error_message(innerValue.value)
        if innerValue.value < min:
            return f"Must be at least {min}"
        if innerValue.value > max:
            return f"Must be less than {max}"

    def set_value():
        if is_valid.value:
            value.set(innerValue.value)

    solara.use_effect(set_value, [innerValue.value])

    solara.InputInt(
        value=innerValue,
        continuous_update=True,
        **kwargs
    )
    if error.value:
        solara.Error(label=error.value, dense=True, text=True, outlined=False)
    