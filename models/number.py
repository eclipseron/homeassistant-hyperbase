class NumberColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns[f"number"] = {"kind": "double", "required": False}
                continue
            else:
                self.__columns[f"number__{dc}"] = {"kind": "double", "required": False}
            
    @property
    def schema(self):
        return self.__columns



class NumnberEntityData:
    def __init__(self,
        device_class: str | None = None,
        state_value: float | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            return {f"sensor__{self.__device_class}": self.__state_value}
        else:
            return {f"sensor": self.__state_value}