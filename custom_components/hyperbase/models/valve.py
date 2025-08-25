class ValveColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns[f"valve_is_open"] = {"kind": "boolean", "required": False}
                self.__columns[f"valve_position"] = {"kind": "integer", "required": False}
                continue
            self.__columns[f"valve__{dc}_is_open"] = {"kind": "boolean", "required": False}
            self.__columns[f"valve__{dc}_position"] = {"kind": "integer", "required": False}

    @property
    def schema(self):
        return self.__columns



class ValveEntityData:
    def __init__(self,
        device_class: str | None = None,
        is_open: bool | None = None,
        position: int | None = None,
        ):
        self._device_class = device_class
        self._is_open = is_open
        self._position = position
    
    @property
    def data(self):
        if self._device_class is not None:
            return {
                f"valve__{self.__device_class}_is_open": self._is_open,
                f"valve__{self.__device_class}_position": self._position
            }
        else:
            return {
                f"valve_is_open": self._is_open,
                f"valve_position": self._position
            }