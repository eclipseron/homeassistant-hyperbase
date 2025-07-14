from typing import Any
from homeassistant.core import State
from homeassistant.helpers.entity_registry import RegistryEntry
from .binary_sensor import BinarySensorColumns, BinarySensorEntityData, BINARY_SENSOR_COLUMNS
from .light import LIGHT_COLUMNS, LightEntityData, LightColumns
from .sensor import SENSOR_COLUMNS, SensorEntityData, SensorColumns
from .switch import SWITCH_COLUMNS, SwitchColumns, SwitchEntityData
from .base import BASE_COLUMNS
from ..const import LOGGER

from homeassistant.const import Platform

COLUMNS_MODELS = {
    Platform.BINARY_SENSOR: BINARY_SENSOR_COLUMNS,
    Platform.LIGHT: LIGHT_COLUMNS,
    Platform.SENSOR: SENSOR_COLUMNS,
    Platform.SWITCH: SWITCH_COLUMNS
}

class DomainDeviceClass:
    def __init__(self, domain: str, device_classes: list[str] = []):
        self.domain = domain
        self.device_clasess = device_classes


def create_schema(entity_domains: list[DomainDeviceClass]) -> dict[str, dict[str, Any]]:
    schema = {**BASE_COLUMNS}
    for entity_domain in entity_domains:
        match entity_domain.domain:
            case Platform.SENSOR:
                _additional_cols = SensorColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.BINARY_SENSOR:
                _additional_cols = BinarySensorColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.SWITCH:
                _additional_cols = SwitchColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.LIGHT:
                _additional_cols = LightColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case _:
                schema = {
                    **schema,
                    f"{entity_domain.domain}":{"kind": "string", "required": False}
                }
                continue
    return schema


def parse_entity_data(entity_entry: RegistryEntry, state: State):
    match entity_entry.domain:
        case Platform.SENSOR:
            device_class = entity_entry.original_device_class
            if device_class is None:
                # use translation_key as class identifier
                # in case device_class = null
                device_class = entity_entry.translation_key
            sensor = SensorEntityData(device_class, state.state)
            return sensor.data
        case Platform.BINARY_SENSOR:
            device_class = entity_entry.original_device_class
            if device_class is None:
                device_class = entity_entry.translation_key
            binary_sensor = BinarySensorEntityData(device_class, state.state)
            return binary_sensor.data
        case Platform.SWITCH:
            device_class = entity_entry.original_device_class
            if device_class is None:
                device_class = entity_entry.translation_key
            switch = SwitchEntityData(device_class, state.state)
            return switch.data
        case Platform.LIGHT:
            hs_color = state.attributes.get("hs_color", None)
            rgb_color = state.attributes.get("rgb_color", None)
            xy_color = state.attributes.get("xy_color", None)
            
            hue = None
            saturation = None
            red = None
            green = None
            blue = None
            x_color = None
            y_color = None
            
            if hs_color is not None:
                hue = hs_color[0]
                saturation = hs_color[1]
            
            if rgb_color is not None:
                red = rgb_color[0]
                green = rgb_color[1]
                blue = rgb_color[2]
            
            if xy_color is not None:
                x_color = xy_color[0]
                y_color = xy_color[1]
            
            light = LightEntityData(
                state_value=state.state,
                brightness=state.attributes.get("brightness", None),
                color_temp_kelvin=state.attributes.get("color_temp_kelvin", None),
                hue=hue,
                saturation=saturation,
                color_temp=state.attributes.get("color_temp", None),
                red=red,
                green=green,
                blue=blue,
                x_color=x_color,
                y_color=y_color
            )
            return light.data
        case _:
            pass