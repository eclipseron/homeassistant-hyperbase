from typing import Any
from .base import BASE_COLUMNS, BaseModel


BINARY_SENSOR_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "is_on": {"kind": "boolean", "required": False},
}

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