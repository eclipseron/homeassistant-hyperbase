import datetime
from typing import Any

from homeassistant.components.sensor.const import SensorDeviceClass
from .base import BASE_COLUMNS, BaseModel

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
                return {f"sensor__{self.__device_class}": float(self.__state_value)}
        else:
            return {f"sensor__unknown": self.__state_value}



class SensorModel:
    def __init__(self,
        base_info: BaseModel,
        device_class: str | None = None,
        last_reset: str | None = None,
        unit_of_measurement: str | None = None,
        value: Any | None = None,
        state_class: str | None = None,
        ):
        value_datetime = None
        value_numeric = None
        value_str = None
        
        
        # try to parse numeric state from str to datetime or float
        try:
            _ = datetime.datetime.fromisoformat(value)
            value_datetime = value
        except:
            try:
                value_numeric = float(value)
            except:
                value_str = value
        
        try:
            state_class = state_class.name
        except AttributeError:
            pass
            # json_data["state_class"] = state.attributes["state_class"]
        self.__data = {
            **base_info.base_data,
            "device_class": device_class,
            "last_reset": last_reset,
            "unit_of_measurement": unit_of_measurement,
            "value_str": value_str,
            "value_numeric": value_numeric,
            "value_datetime": value_datetime,
            "state_class": state_class,
        }
    
    @property
    def data(self):
        return self.__data