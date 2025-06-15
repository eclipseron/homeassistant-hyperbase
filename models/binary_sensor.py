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