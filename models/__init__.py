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
    
    if state.state == "unknown":
        return None
    
    match entity_entry.domain:
        case Platform.AIR_QUALITY:
            from homeassistant.components.air_quality import (
                ATTR_AQI, ATTR_CO, ATTR_CO2, ATTR_N2O, ATTR_NO,
                ATTR_NO2, ATTR_OZONE, ATTR_PM_0_1, ATTR_PM_2_5, ATTR_PM_10,
                ATTR_SO2
            )
            
            airq = AirQEntityData(
                air_quality_index=state.attributes.get(ATTR_AQI),
                carbon_dioxide=state.attributes.get(ATTR_CO),
                carbon_monoxide=state.attributes.get(ATTR_CO2),
                nitrogen_dioxide=state.attributes.get(ATTR_N2O),
                nitrogen_monoxide=state.attributes.get(ATTR_NO),
                nitrogen_oxide=state.attributes.get(ATTR_NO2),
                ozone=state.attributes.get(ATTR_OZONE),
                particulate_matter_0_1=state.attributes.get(ATTR_PM_0_1),
                particulate_matter_2_5=state.attributes.get(ATTR_PM_2_5),
                particulate_matter_10=state.attributes.get(ATTR_PM_10),
                sulphur_dioxide=state.attributes.get(ATTR_SO2),
            )
            return airq.data
        
        case Platform.ALARM_CONTROL_PANEL:
            alarm = AlarmEntityData(state_value=state.state)
            return alarm.data
        
        case Platform.BINARY_SENSOR:
            binary_sensor = BinarySensorEntityData(device_class, state_value= state.state == STATE_ON)
            return binary_sensor.data
        
        case Platform.BUTTON:
            button = ButtonEntityData(state_value=state.state)
            return button.data
        
        case Platform.CALENDAR:
            calendar = CalendarEntityData(state_value=state.state)
            return calendar.data

        case Platform.CAMERA:
            camera = CameraEntityData(state_value=state.state)
            return camera.data
        
        case Platform.CLIMATE:
            from homeassistant.components.climate.const import (
                ATTR_CURRENT_HUMIDITY, ATTR_CURRENT_TEMPERATURE, ATTR_FAN_MODE,
                ATTR_HVAC_ACTION, ATTR_HVAC_MODE, ATTR_PRESET_MODE, ATTR_SWING_MODE,
                ATTR_SWING_HORIZONTAL_MODE, ATTR_HUMIDITY, ATTR_TARGET_TEMP_HIGH,
                ATTR_TARGET_TEMP_LOW
            )
            climate = ClimateEntityData(
                current_humidity=state.attributes.get(ATTR_CURRENT_HUMIDITY, None),
                current_temperature=state.attributes.get(ATTR_CURRENT_TEMPERATURE, None),
                fan_mode=state.attributes.get(ATTR_FAN_MODE, None),
                hvac_action=state.attributes.get(ATTR_HVAC_ACTION, None),
                hvac_mode=state.attributes.get(ATTR_HVAC_MODE, None),
                preset_mode=state.attributes.get(ATTR_PRESET_MODE, None),
                swing_mode=state.attributes.get(ATTR_SWING_MODE, None),
                swing_horizontal_mode=state.attributes.get(ATTR_SWING_HORIZONTAL_MODE, None),
                target_humidity=state.attributes.get(ATTR_HUMIDITY, None),
                target_temperature=state.attributes.get("temperature", None),
                target_temperature_high=state.attributes.get(ATTR_TARGET_TEMP_HIGH, None),
                target_temperature_low=state.attributes.get(ATTR_TARGET_TEMP_LOW, None),
            )
            return climate.data
        
        case Platform.CONVERSATION:
            conversation = ConversationEntityData(state_value=state.state)
            return conversation.data
        
        case Platform.COVER:
            from homeassistant.components.cover import CoverState
            cover = CoverEntityData(device_class, state_value = state.state == CoverState.CLOSED)
            return cover.data
        
        case Platform.DATETIME:
            datetime = DateTimeEntityData(datetime_iso=state.state)
            return datetime.data
        
        case Platform.DATE:
            date = DateEntityData(date_iso=state.state)
            return date.data
        
        case Platform.DEVICE_TRACKER:
            from homeassistant.components.device_tracker import ATTR_BATTERY
            device_tracker = DeviceTrackerEntityData(
                battery=state.attributes.get(ATTR_BATTERY, None),
                latitude=state.attributes.get("latitude", None),
                longitude=state.attributes.get("longitude", None),
            )
            return device_tracker.data
        
        case Platform.EVENT:
            event = EventEntityData(state_value=state.state)
            return event.data
        
        case Platform.FAN:
            from homeassistant.components.fan import (
                ATTR_DIRECTION,
                ATTR_OSCILLATING,
                ATTR_PERCENTAGE,
                ATTR_PRESET_MODE
                )
            
            fan = FanEntityData(
                direction = state.attributes.get(ATTR_DIRECTION, None),
                is_on = state.state == STATE_ON,
                oscillating = state.attributes.get(ATTR_OSCILLATING, None),
                percentage = state.attributes.get(ATTR_PERCENTAGE, None),
                mode = state.attributes.get(ATTR_PRESET_MODE, None),
            )
            return fan.data
        
        case Platform.HUMIDIFIER:
            from homeassistant.components.humidifier.const import (
                ATTR_ACTION,
                ATTR_CURRENT_HUMIDITY,
                ATTR_HUMIDITY
                )
            
            humidifier = HumidifierEntityData(
                device_class=device_class,
                action=state.attributes.get(ATTR_ACTION, None),
                current_humidity=state.attributes.get(ATTR_CURRENT_HUMIDITY, None),
                is_on=state.state==STATE_ON,
                mode=state.attributes.get("mode", None),
                target=state.attributes.get(ATTR_HUMIDITY, None),
            )
            return humidifier.data
        
        case Platform.LAWN_MOWER:
            mower = LawnMowerEntityData(state_value=state.state)
            return mower.data
        
        case Platform.LIGHT:
            from homeassistant.components.light import (
                ATTR_BRIGHTNESS, ATTR_COLOR_TEMP_KELVIN,
                ATTR_HS_COLOR, ATTR_RGB_COLOR, ATTR_XY_COLOR
            )
            
            hs_color = state.attributes.get(ATTR_HS_COLOR, None)
            rgb_color = state.attributes.get(ATTR_RGB_COLOR, None)
            xy_color = state.attributes.get(ATTR_XY_COLOR, None)
            
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
                state_value=state.state == STATE_ON,
                brightness=state.attributes.get(ATTR_BRIGHTNESS, None),
                color_temp_kelvin=state.attributes.get(ATTR_COLOR_TEMP_KELVIN, None),
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
        
        case Platform.LOCK:
            lock = LockEntityData(state_value=state.state)
            return lock.data
        
        case Platform.NUMBER:
            number = NumberEntityData(device_class, float(state.state))
            return number.data
        
        case Platform.REMOTE:
            remote = RemoteEntityData(state.state)
            return remote.data
        
        case Platform.ASSIST_SATELLITE:
            satellite = SatelliteEntityData(state.state)
            return satellite.data
        
        case Platform.SELECT:
            select = SelectEntityData(state.state)
            return select.data
        
        case Platform.SENSOR:
            sensor = SensorEntityData(device_class, state.state)
            return sensor.data
        
        case Platform.SIREN:
            siren = SirenEntityData(state.state==STATE_ON)
            return siren.data
        
        case Platform.SWITCH:
            switch = SwitchEntityData(device_class, state.state==STATE_ON)
            return switch.data
        
        case Platform.TEXT:
            text = TextEntityData(state.state)
            return text.data
        
        case Platform.TIME:
            time = TimeEntityData(state.state)
            return time.data
        
        case Platform.VACUUM:
            from homeassistant.components.vacuum import ATTR_FAN_SPEED, ATTR_STATUS
            vacuum = VacuumEntityData(
                vacuum_fan_speed=state.attributes.get(ATTR_FAN_SPEED, None),
                vacuum_status=state.attributes.get(ATTR_STATUS, None),
            )
            return vacuum.data
        
        case Platform.VALVE:
            from homeassistant.components.valve import ATTR_CURRENT_POSITION, STATE_OPEN
            valve = ValveEntityData(
                device_class=device_class,
                is_open=state.state==STATE_OPEN,
                position=state.attributes.get(ATTR_CURRENT_POSITION, None)
                )
            return valve.data
        
        case Platform.WATER_HEATER:
            from homeassistant.components.water_heater import (
                ATTR_CURRENT_TEMPERATURE, ATTR_TARGET_TEMP_HIGH,
                ATTR_TARGET_TEMP_LOW, ATTR_TEMPERATURE, ATTR_AWAY_MODE
            )
            
            is_away = state.attributes.get(ATTR_AWAY_MODE, None)
            if is_away is not None:
                is_away = is_away == STATE_ON
            
            heater = WaterHeaterEntityData(
                temperature=state.attributes.get(ATTR_CURRENT_TEMPERATURE, None),
                target_temperature=state.attributes.get(ATTR_TEMPERATURE, None),
                target_temperature_high=state.attributes.get(ATTR_TARGET_TEMP_HIGH, None),
                target_temperature_low=state.attributes.get(ATTR_TARGET_TEMP_LOW, None),
                mode=state.state,
                is_away=is_away,
            )
            return heater.data

        case Platform.WEATHER:
            from homeassistant.components.weather.const import (
                ATTR_WEATHER_CLOUD_COVERAGE, ATTR_WEATHER_HUMIDITY,
                ATTR_WEATHER_APPARENT_TEMPERATURE, ATTR_WEATHER_DEW_POINT,
                ATTR_WEATHER_PRESSURE, ATTR_WEATHER_TEMPERATURE,
                ATTR_WEATHER_VISIBILITY, ATTR_WEATHER_WIND_GUST_SPEED,
                ATTR_WEATHER_WIND_SPEED, ATTR_WEATHER_OZONE, ATTR_WEATHER_WIND_BEARING,
                ATTR_WEATHER_UV_INDEX
            )
            
            cloud_coverage = state.attributes.get(ATTR_WEATHER_CLOUD_COVERAGE, None)
            if cloud_coverage is not None:
                cloud_coverage = int(cloud_coverage)
            
            wind_bearing = state.attributes.get(ATTR_WEATHER_WIND_BEARING, None)
            if wind_bearing is not None:
                wind_bearing = str(wind_bearing)
            
            
            weather = WeatherEntityData(
                cloud_coverage=cloud_coverage,
                condition=state.state,
                humidity=state.attributes.get(ATTR_WEATHER_HUMIDITY ,None),
                feels_like_temperature=state.attributes.get(ATTR_WEATHER_APPARENT_TEMPERATURE ,None),
                dew_point=state.attributes.get(ATTR_WEATHER_DEW_POINT ,None),
                pressure=state.attributes.get(ATTR_WEATHER_PRESSURE ,None),
                temperature=state.attributes.get(ATTR_WEATHER_TEMPERATURE ,None),
                uv_index=state.attributes.get(ATTR_WEATHER_UV_INDEX ,None),
                visibility=state.attributes.get(ATTR_WEATHER_VISIBILITY ,None),
                wind_gust_speed=state.attributes.get(ATTR_WEATHER_WIND_GUST_SPEED ,None),
                wind_speed=state.attributes.get(ATTR_WEATHER_WIND_SPEED ,None),
                ozone=state.attributes.get(ATTR_WEATHER_OZONE ,None),
                wind_bearing=wind_bearing,
            )
            return weather.data
        case _:
            pass