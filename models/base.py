"""
Base model for hyperbase collections.
"""

from typing import Any


class BaseModel:
    base_columns: dict[dict[str, Any]] = {
        "integration_id":{
            "kind": "string",
            "required": True,
        },
        "entity_id":{
            "kind": "string",
            "required": True,
        },
        "hass_device_id":{
            "kind": "string",
            "required": False,
        },
        "domain":{
            "kind": "string",
            "required": False,
        },
        "product_id":{
            "kind": "string",
            "required": False,
        },
        "manufacturer":{
            "kind": "string",
            "required": False,
        },
        "model_name":{
            "kind": "string",
            "required": False,
        },
        "model_id":{
            "kind": "string",
            "required": False,
        },
        "name_default":{
            "kind": "string",
            "required": False,
        },
        "name_by_user":{
            "kind": "string",
            "required": False,
        },
    }

    def __init__(self):
        """Initialize base class"""