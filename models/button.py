from typing import Any
from .base import BaseModel

class ButtonModel(BaseModel):
    __button_columns: dict[dict[str, Any]] = {
        "device_class":{
            "kind": "string",
            "required": False,
        }
    }
    
    def __init__(self):
        self.__columns = {**self.__button_columns, **super().base_columns}
        """Initialize sensor model"""
    
    
    def __init__(self,
        connector_serial_number: str,
        connector_entity: str,
        entity_id: str,
        hass_device_id: str | None = None,
        domain: str | None = None,
        product_id: str | None = None,
        manufacturer: str | None = None,
        model_name: str | None = None,
        model_id: str | None = None,
        name_default: str | None = None,
        name_by_user: str | None = None,
        device_class: str | None = None
        ):
        super().__init__(
            connector_serial_number,
            connector_entity,
            entity_id,
            hass_device_id,
            domain,
            product_id,
            manufacturer,
            model_name,
            model_id,
            name_default,
            name_by_user
        )
        self.__data = {
            **super().base_data,
            "device_class": device_class,
        }
    
    @property
    def columns(self):
        return self.__columns
    
    @property
    def data(self):
        return self.__data