from typing import Any
from homeassistant.core import State
from homeassistant.helpers.entity_registry import RegistryEntry
from homeassistant.const import STATE_ON
from .air_quality import *
from .alarm import *
from .binary_sensor import *
from .button import *
from .calendar import *
from .camera import *
from .climate import *
from .conversation import *
from .cover import *
from .date_time import *
from .date import *
from .device_tracker import *
from .event import *
from .fan import *
from .humidifier import *
from .lawn_mower import *
from .light import *
from .lock import *
from .number import *
from .remote import *
from .satellite import *
from .select import *
from .sensor import *
from .siren import *
from .switch import *
from .text import *
from .time import *
from .vacuum import *
from .valve import *
from .water_heater import *
from .weather import *
from .base import BASE_COLUMNS

from homeassistant.const import Platform

class DomainDeviceClass:
    def __init__(self, domain: str, device_classes: list[str] = []):
        self.domain = domain
        self.device_clasess = device_classes


def create_schema(entity_domains: list[DomainDeviceClass]) -> dict[str, dict[str, Any]]:
    schema = {**BASE_COLUMNS}
    for entity_domain in entity_domains:
        match entity_domain.domain:
            case Platform.AIR_QUALITY:
                _additional_cols = AirQColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.ALARM_CONTROL_PANEL:
                _additional_cols = AlarmColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.BINARY_SENSOR:
                _additional_cols = BinarySensorColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.BUTTON:
                _additional_cols = ButtonColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.CALENDAR:
                _additional_cols = CalendarColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.CAMERA:
                _additional_cols = CameraColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.CLIMATE:
                _additional_cols = ClimateColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.CONVERSATION:
                _additional_cols = ConversationColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.COVER:
                _additional_cols = CoverColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.DATETIME:
                _additional_cols = DateTimeColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.DATE:
                _additional_cols = DateColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.DEVICE_TRACKER:
                _additional_cols = DeviceTrackerColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.EVENT:
                _additional_cols = EventColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.FAN:
                _additional_cols = FanColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.HUMIDIFIER:
                _additional_cols = HumidifierColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.LAWN_MOWER:
                _additional_cols = LawnMowerColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.LIGHT:
                _additional_cols = LightColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.LOCK:
                _additional_cols = LockColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.NUMBER:
                _additional_cols = NumberColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.REMOTE:
                _additional_cols = RemoteColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.ASSIST_SATELLITE:
                _additional_cols = SatelliteColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.SELECT:
                _additional_cols = SelectColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.SENSOR:
                _additional_cols = SensorColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.SIREN:
                _additional_cols = SirenColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.SWITCH:
                _additional_cols = SwitchColumns(entity_domain.device_clasess)
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.TEXT:
                _additional_cols = TextColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.TIME:
                _additional_cols = TimeColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.VACUUM:
                _additional_cols = VacuumColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.WATER_HEATER:
                _additional_cols = WaterHeaterColumns()
                schema = {**schema, **_additional_cols.schema}
                continue
            case Platform.WEATHER:
                _additional_cols = WeatherColumns()
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
    device_class = entity_entry.original_device_class
    if device_class is None:
        # use translation_key as class identifier
        # in case device_class = null
        device_class = entity_entry.translation_key
    
    _state = None
    match entity_entry.domain:
        case Platform.SENSOR:
            if state.state != "unknown":
                _state = state.state
            sensor = SensorEntityData(device_class, state.state)
            return sensor.data
        case Platform.BINARY_SENSOR:
            if state.state != "unknown":
                _state = state.state == STATE_ON
            binary_sensor = BinarySensorEntityData(device_class, _state)
            return binary_sensor.data
        case Platform.SWITCH:
            if state.state != "unknown":
                _state = state.state == STATE_ON
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
            
            if state.state != "unknown":
                _state = state.state == STATE_ON
            
            light = LightEntityData(
                state_value=_state,
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