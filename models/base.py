"""
Base model for hyperbase collections.
"""
from typing import Any


BASE_COLUMNS = {
    "connector_serial_number": {"kind": "string", "required": True},
    "connector_entity": {"kind": "string", "required": True},
    "product_id": {"kind": "string", "required": False},
    "name_default": {"kind": "string", "required": False},
    "name_by_user": {"kind": "string", "required": False},
    "area_id": {"kind": "string", "required": False},
    "status_reload": {"kind": "string", "required": False}
}

class BaseModel:
    
    def __init__(self,
        connector_serial_number: str,
        connector_entity: str,
        product_id: str | None = None,
        name_default: str | None = None,
        name_by_user: str | None = None,
        area_id: str | None = None,
        ):
        """Create new object to hold device metadata"""
        self.__base_data: dict[str, Any] = {
            "connector_serial_number": connector_serial_number,
            "connector_entity": connector_entity,
            "product_id": product_id,
            "name_default": name_default,
            "name_by_user": name_by_user,
            "area_id": area_id
        }
    
    
    @property
    def base_data(self) -> dict[str, Any]:
        return self.__base_data