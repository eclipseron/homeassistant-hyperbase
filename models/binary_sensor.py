from typing import Any
from .base import BASE_COLUMNS, BaseModel
from homeassistant.components.binary_sensor import BinarySensorDeviceClass


BINARY_SENSOR_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "is_on": {"kind": "boolean", "required": False},
}

class BinarySensorColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            self.__columns[f"binary_sensor__{dc}"] = {"kind": "boolean", "required": False}
    @property
    def schema(self):
        return self.__columns


class BinarySensorEntityData:
    def __init__(self, device_class: str | None = None, state_value: Any | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            return {f"binary_sensor__{self.__device_class}": self.__state_value == "on"}
        else:
            return {f"binary_sensor__unknown": self.__state_value == "on"}


class BinarySensorModel():
    """asdad"""
    def __init__(self,
        base_info: BaseModel,
        device_class: str | None = None,
        is_on: bool | None = None,
    ):
        self.__data = {
            **base_info.base_data,
            "device_class": device_class,
            "is_on": is_on,
        }
    
    @property
    def data(self):
        return self.__data