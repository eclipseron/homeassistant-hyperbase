from typing import Any

class ClimateColumns:
    def __init__(self):
        self.__columns = {
            "climate_current_humidity": {"kind": "double", "required": False},
            "climate_current_temperature": {"kind": "double", "required": False},
            "climate_fan_mode": {"kind": "string", "required": False},
            "climate_hvac_action": {"kind": "string", "required": False},
            "climate_hvac_mode": {"kind": "string", "required": False},
            "climate_preset_mode": {"kind": "string", "required": False},
            "climate_swing_mode": {"kind": "string", "required": False},
            "climate_swing_horizontal_mode": {"kind": "string", "required": False},
            "climate_target_humidity": {"kind": "double", "required": False},
            "climate_target_temperature": {"kind": "double", "required": False},
            "climate_target_temperature_high": {"kind": "double", "required": False},
            "climate_target_temperature_low": {"kind": "double", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class ClimateEntityData:
    def __init__(self,
        current_humidity: float | None = None,
        current_temperature: float | None = None,
        fan_mode: str | None = None,
        hvac_action: str | None = None,
        hvac_mode: str | None = None,
        preset_mode: str | None = None,
        swing_mode: str | None = None,
        swing_horizontal_mode: str | None = None,
        target_humidity: float | None = None,
        target_temperature: float | None = None,
        target_temperature_high: float | None = None,
        target_temperature_low: float | None = None,
        ):
        self._current_humidity = current_humidity
        self._current_temperature = current_temperature
        self._fan_mode = fan_mode
        self._hvac_action = hvac_action
        self._hvac_mode = hvac_mode
        self._preset_mode = preset_mode
        self._swing_mode = swing_mode
        self._swing_horizontal_mode = swing_horizontal_mode
        self._target_humidity = target_humidity
        self._target_temperature = target_temperature
        self._target_temperature_high = target_temperature_high
        self._target_temperature_low = target_temperature_low
    
    @property
    def data(self):
        return {
            "climate_current_humidity": self._climate_current_humidity,
            "climate_current_temperature": self._climate_current_temperature,
            "climate_fan_mode": self._climate_fan_mode,
            "climate_hvac_action": self._climate_hvac_action,
            "climate_hvac_mode": self._climate_hvac_mode,
            "climate_preset_mode": self._climate_preset_mode,
            "climate_swing_mode": self._climate_swing_mode,
            "climate_swing_horizontal_mode": self._climate_swing_horizontal_mode,
            "climate_target_humidity": self._climate_target_humidity,
            "climate_target_temperature": self._climate_target_temperature,
            "climate_target_temperature_high": self._climate_target_temperature_high,
            "climate_target_temperature_low": self._climate_target_temperature_low,
        }