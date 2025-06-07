
from typing import Any
from .base import BaseModel

class SensorModel(BaseModel):
    sensor_columns: dict[dict[str, Any]] = {
        "device_class":{
            "kind": "string",
            "required": False,
        },
        "last_reset":{
            "kind": "timestamp",
            "required": False,
        },
        "unit_of_measurement":{
            "kind": "string",
            "required": False,
        },
        "value_str":{
            "kind": "string",
            "required": False,
        },
        "value_numeric":{
            "kind": "double",
            "required": False,
        },
        "value_datetime":{
            "kind": "timestamp",
            "required": False,
        },
        "state_class":{
            "kind": "string",
            "required": False,
        },
    }
    
    def __init__(self):
        self.sensor_columns = {**self.sensor_columns, **self.base_columns}
        """Initialize sensor model"""
    
    @property
    def columns(self):
        return self.sensor_columns