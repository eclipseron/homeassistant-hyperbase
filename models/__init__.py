from datetime import datetime
from homeassistant.core import State
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_registry import RegistryEntry
from .binary_sensor import BinarySensorModel, BINARY_SENSOR_COLUMNS
from .light import LIGHT_COLUMNS, LightModel
from .sensor import SENSOR_COLUMNS, SensorModel
from .switch import SWITCH_COLUMNS, SwitchModel
from .base import BaseModel

from homeassistant.const import Platform

COLUMNS_MODELS = {
    Platform.BINARY_SENSOR: BINARY_SENSOR_COLUMNS,
    Platform.LIGHT: LIGHT_COLUMNS,
    Platform.SENSOR: SENSOR_COLUMNS,
    Platform.SWITCH: SWITCH_COLUMNS
}

def parse_data(connector_serial_number: str,
            connector_entity: str,
            device_entry: DeviceEntry,
            entity_entry: RegistryEntry,
            state: State,
            last_reported: datetime):
    """parse data """
    
    base_info = BaseModel(
        connector_serial_number=connector_serial_number,
        connector_entity=connector_entity,
        entity_id=entity_entry.entity_id,
        product_id=device_entry.dict_repr["identifiers"][0][1],
        manufacturer=device_entry.manufacturer,
        model_name=device_entry.model,
        model_id=device_entry.model_id,
        name_default=device_entry.name,
        name_by_user=device_entry.name_by_user,
        area_id=device_entry.area_id,
    )
    match entity_entry.domain:
        case Platform.SENSOR:
            sensor = SensorModel(
                base_info,
                device_class=entity_entry.original_device_class,
                last_reset = last_reported,
                unit_of_measurement=entity_entry.unit_of_measurement,
                value=state.state,
                state_class=entity_entry.capabilities.get("state_class", None)
            )
            return sensor.data

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
            
            light = LightModel(
                base_info,
                brightness=state.attributes.get("brightness", None),
                color_mode=state.attributes.get("color_mode", None),
                color_temp_kelvin=state.attributes.get("color_temp_kelvin", None),
                effect=state.attributes.get("effect", None),
                hue=hue,
                saturation=saturation,
                is_on=state.state == "on",
                max_color_temp_kelvin=state.attributes.get("max_color_temp_kelvin", None),
                min_color_temp_kelvin=state.attributes.get("min_color_temp_kelvin", None),
                color_temp=state.attributes.get("color_temp", None),
                red=red,
                green=green,
                blue=blue,
                x_color=x_color,
                y_color=y_color,
            )
            return light.data
        
        
        case Platform.BINARY_SENSOR:
            binary_sensor = BinarySensorModel(
                base_info,
                device_class=entity_entry.original_device_class,
                is_on=state.state == "on"
            )
            return binary_sensor.data
        case _:
            return None