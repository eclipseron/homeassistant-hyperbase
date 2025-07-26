import datetime
from typing import Any

from homeassistant.components.sensor.const import SensorDeviceClass
from .base import BASE_COLUMNS

SENSOR_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "value_str": {"kind": "string", "required": False},
    "value_numeric": {"kind": "double", "required": False},
    "value_datetime": {"kind": "timestamp", "required": False},
    "state_class": {"kind": "string", "required": False}
}

class SensorColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns[f"sensor"] = {"kind": "string", "required": False}
                continue
            if dc == SensorDeviceClass.TIMESTAMP or dc == SensorDeviceClass.DATE:
                self.__columns[f"sensor__{dc}"] = {"kind": "timestamp", "required": False}
            elif dc == SensorDeviceClass.ENUM:
                self.__columns[f"sensor__{dc}"] = {"kind": "string", "required": False}
            else:
                self.__columns[f"sensor__{dc}"] = {"kind": "double", "required": False}
            
    @property
    def schema(self):
        return self.__columns



class SensorEntityData:
    def __init__(self, device_class: str | None = None, state_value: Any | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            if self.__device_class == SensorDeviceClass.TIMESTAMP or self.__device_class == SensorDeviceClass.DATE or self.__device_class == SensorDeviceClass.ENUM:
                return {f"sensor__{self.__device_class}": self.__state_value}
            else:
                try:
                    if self.__state_value == "unknown":
                        return {f"sensor__{self.__device_class}": None}
                    return {f"sensor__{self.__device_class}": float(self.__state_value)}
                except ValueError:
                    return {f"sensor__{self.__device_class}": self.__state_value}
        else:
            return {f"sensor": self.__state_value}