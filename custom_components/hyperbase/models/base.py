"""
Base model for hyperbase collections.
"""

BASE_COLUMNS = {
    "hass_connector_entity": {"kind": "string", "required": True},
    "hass_product_id": {"kind": "string", "required": False},
    "hass_name_default": {"kind": "string", "required": False},
    "hass_name_by_user": {"kind": "string", "required": False},
    "hass_area_id": {"kind": "string", "required": False},
    "hass_status": {"kind": "string", "required": False},
    "hass_record_date": {"kind": "timestamp", "required": False}
}