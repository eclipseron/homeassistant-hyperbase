"""
Base model for hyperbase collections.
"""

BASE_COLUMNS = {
    "connector_serial_number": {"kind": "string", "required": True},
    "connector_entity": {"kind": "string", "required": True},
    "product_id": {"kind": "string", "required": False},
    "name_default": {"kind": "string", "required": False},
    "name_by_user": {"kind": "string", "required": False},
    "area_id": {"kind": "string", "required": False},
    "status": {"kind": "string", "required": False},
    "record_date": {"kind": "timestamp", "required": False}
}