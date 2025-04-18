
import solara

from pydantic import field_validator

from cds_core.state import BaseState
from ..base_marker import BaseMarker
from ..base_component_state import BaseComponentState
from ..state import LOCAL_STATE

import enum
from typing import Any, cast


class Marker(enum.Enum, BaseMarker):
    mark1 = enum.auto()
    mark2 = enum.auto()
    mark3 = enum.auto()
    mark4 = enum.auto()
    
class ComponentState(BaseState, BaseComponentState):
    current_step: Marker = Marker.mark1
    stage_id: str = "test_page"
    
    button_clicked: bool = False
    
    @field_validator("current_step", mode="before")
    def convert_int_to_enum(cls, v: Any) -> Marker:
        if isinstance(v, int):
            return Marker(v)
        return v
    
    @property
    def mark2_gate(self) -> bool:
        return self.button_clicked
    
    @property
    def mark3_gate(self) -> bool:
        return LOCAL_STATE.value.question_completed("mc-2")
    
    @property
    def mark4_gate(self) -> bool:
        return LOCAL_STATE.value.question_completed("fr-1")


    
COMPONENT_STATE = solara.reactive(ComponentState())