import os
from functools import cached_property
from typing import Annotated, Dict, Union

from glue.core import Data, DataCollection, Session
from glue_jupyter import JupyterApplication
from pydantic import BaseModel, Field

from .base_states import BaseAppState, BaseState

update_db_init = not (os.getenv("CDS_DISABLE_DB", "false").strip().lower() == "true")
show_team_interface_init = (
    os.getenv("CDS_SHOW_TEAM_INTERFACE", "false").strip().lower() == "true"
)


class Student(BaseModel):
    id: int = None


class Classroom(BaseModel):
    class_info: dict | None = {}
    size: int = 0


class Speech(BaseModel):
    pitch: float = 1.0
    rate: float = 1.0
    autoread: bool = False
    voice: str | None = None


class AppState(BaseAppState):
    drawer: bool = True
    speed_menu: bool = False
    loading_status_message: str = ""
    student: Student = Student()
    classroom: Classroom = Classroom()
    update_db: bool = Field(update_db_init, exclude=True)
    show_team_interface: bool = Field(True, exclude=True)
    allow_advancing: bool = True
    speech: Speech = Speech()
    educator: bool = False

    @cached_property
    def _glue_app(self) -> JupyterApplication:
        return JupyterApplication()

    @cached_property
    def glue_data_collection(self) -> DataCollection:
        return self._glue_app.data_collection

    @cached_property
    def glue_session(self) -> Session:
        return self._glue_app.session

    def add_or_update_data(self, data: Data):
        if data.label in self.glue_data_collection:
            existing = self.glue_data_collection[data.label]
            existing.update_values_from_data(data)
            return existing
        else:
            self.glue_data_collection.append(data)
            return data
