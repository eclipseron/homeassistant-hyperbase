import datetime
from typing import Any
from .base import BaseModel, BASE_COLUMNS

SENSOR_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "last_reset": {"kind": "timestamp", "required": False},
    "unit_of_measurement": {"kind": "string", "required": False},
    "value_str": {"kind": "string", "required": False},
    "value_numeric": {"kind": "double", "required": False},
    "value_datetime": {"kind": "timestamp", "required": False},
    "state_class": {"kind": "string", "required": False},
}

class SensorModel():
    def __init__(self,
        base_info: BaseModel,
        # connector_serial_number: str,
        # connector_entity: str,
        # entity_id: str,
        # # hass_device_id: str | None = None,
        # # domain: str | None = None,
        # product_id: str | None = None,
        # manufacturer: str | None = None,
        # model_name: str | None = None,
        # model_id: str | None = None,
        # name_default: str | None = None,
        # name_by_user: str | None = None,
        # area_id: str | None = None,
        device_class: str | None = None,
        last_reset: str | None = None,
        unit_of_measurement: str | None = None,
        value: Any | None = None,
        state_class: str | None = None,
        ):
        # super().__init__(
        #     connector_serial_number,
        #     connector_entity,
        #     entity_id,
        #     # hass_device_id,
        #     # domain,
        #     product_id,
        #     manufacturer,
        #     model_name,
        #     model_id,
        #     name_default,
        #     name_by_user,
        #     area_id
        # )
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