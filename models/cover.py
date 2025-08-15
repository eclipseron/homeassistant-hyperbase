class CoverColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns[f"cover_is_closed"] = {"kind": "boolean", "required": False}
                continue
            else:
                self.__columns[f"cover__{dc}_is_closed"] = {"kind": "boolean", "required": False}
            
    @property
    def schema(self):
        return self.__columns


class CoverEntityData:
    def __init__(self, device_class: str | None = None, state_value: bool | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            return {f"cover__{self.__device_class}_is_closed": self.__state_value}
        else:
            return {f"cover_is_closed": self.__state_value}