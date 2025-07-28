class WaterHeaterColumns:
    def __init__(self):
        self.__columns = {
            "heater_temperature": {"kind": "double", "required": False},
            "heater_target_temperature": {"kind": "double", "required": False},
            "heater_target_temperature_high": {"kind": "double", "required": False},
            "heater_target_temperature_low": {"kind": "double", "required": False},
            "heater_mode": {"kind": "string", "required": False},
            "heater_is_away": {"kind": "boolean", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class WaterHeaterEntityData:
    def __init__(self,
        temperature: float | None = None,
        target_temperature: float | None = None,
        target_temperature_high: float | None = None,
        target_temperature_low: float | None = None,
        mode: str | None = None,
        is_away: bool | None = None,
        ):
        self._temperature = temperature
        self._target_temperature = target_temperature
        self._target_temperature_high = target_temperature_high
        self._target_temperature_low = target_temperature_low
        self._mode = mode
        self._is_away = is_away
    
    @property
    def data(self):
        return {
            "heater_temperature": self._temperature,
            "heater_target_temperature": self._target_temperature,
            "heater_target_temperature_high": self._target_temperature_high,
            "heater_target_temperature_low": self._target_temperature_low,
            "heater_mode": self._mode,
            "heater_is_away": self._is_away,
        }