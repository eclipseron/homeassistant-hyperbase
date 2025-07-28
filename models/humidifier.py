class HumidifierColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns["humidifier_action"] = {"kind": "string", "required": False}
                self.__columns["humidifier_current_humidity"] = {"kind": "double", "required": False}
                self.__columns["humidifier_is_on"] = {"kind": "boolean", "required": False}
                self.__columns["humidifier_mode"] = {"kind": "string", "required": False}
                self.__columns["humidifier_target"] = {"kind": "double", "required": False}
                continue
            else:
                self.__columns[f"{dc}_action"] = {"kind": "string", "required": False}
                self.__columns[f"{dc}_current_humidity"] = {"kind": "double", "required": False}
                self.__columns[f"{dc}_is_on"] = {"kind": "boolean", "required": False}
                self.__columns[f"{dc}_mode"] = {"kind": "string", "required": False}
                self.__columns[f"{dc}_target"] = {"kind": "double", "required": False}

    @property
    def schema(self):
        return self.__columns


class HumidifierEntityData:
    def __init__(self,
        device_class: str | None = None,
        action: str | None = None,
        current_humidity: float | None = None,
        is_on: bool | None = None,
        mode: str | None = None,
        target: bool | None = None,
        ):
        self._device_class = device_class
        self._action = action
        self._current_humidity = current_humidity
        self._is_on = is_on
        self._mode = mode
        self._target = target
        
    @property
    def data(self):
        if self._device_class is not None:
            return {
                f"{self._device_class}_action": self._action,  
                f"{self._device_class}_current_humidity": self._current_humidity,  
                f"{self._device_class}_is_on": self._is_on,  
                f"{self._device_class}_mode": self._mode,  
                f"{self._device_class}_target": self._target,
            }
        else:
            return {
                f"humidifier_action": self._action,  
                f"humidifier_current_humidity": self._current_humidity,  
                f"humidifier_is_on": self._is_on,  
                f"humidifier_mode": self._mode,  
                f"humidifier_target": self._target,
            }