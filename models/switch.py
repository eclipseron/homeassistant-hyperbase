from typing import Any
from .base import BASE_COLUMNS, BaseModel



SWITCH_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "is_on": {"kind": "boolean", "required": False},
}

class SwitchModel(BaseModel):
    """asdasd"""