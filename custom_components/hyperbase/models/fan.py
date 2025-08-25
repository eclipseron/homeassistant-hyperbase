class FanColumns:
    def __init__(self):
        self.__columns = {
            "fan_direction": {"kind": "string", "required": False},
            "fan_is_on": {"kind": "boolean", "required": False},
            "fan_oscillating": {"kind": "boolean", "required": False},
            "fan_percentage": {"kind": "integer", "required": False},
            "fan_mode": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class FanEntityData:
    def __init__(self,
        direction: str | None = None,
        is_on: bool | None = None,
        oscillating: bool | None = None,
        percentage: int | None = None,
        mode: str | None = None,
        ):
        self._direction = direction
        self._is_on = is_on
        self._oscillating = oscillating
        self._percentage = percentage
        self._mode = mode
        
    @property
    def data(self):
        return {
            "fan_direction": self._direction,
            "fan_is_on": self._is_on,
            "fan_oscillating": self._oscillating,
            "fan_percentage": self._percentage,
            "fan_mode": self._mode,
        }