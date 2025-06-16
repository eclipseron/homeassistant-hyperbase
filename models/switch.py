from typing import Any
from .base import BASE_COLUMNS, BaseModel



SWITCH_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "is_on": {"kind": "boolean", "required": False},
}


class SwitchColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            self.__columns[f"switch__{dc}"] = {"kind": "boolean", "required": False}
    @property
    def schema(self):
        return self.__columns



class SwitchEntityData:
    def __init__(self, device_class: str | None = None, state_value: Any | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            return {f"switch__{self.__device_class}": self.__state_value == "on"}
        else:
            return {f"switch__unknown": self.__state_value == "on"}



class SwitchModel(BaseModel):
    """asdasd"""