class BinarySensorColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            if dc == "unknown":
                self.__columns[f"binary_sensor"] = {"kind": "boolean", "required": False}
                continue    
            self.__columns[f"binary_sensor__{dc}"] = {"kind": "boolean", "required": False}
    @property
    def schema(self):
        return self.__columns


class BinarySensorEntityData:
    def __init__(self,
            device_class: str | None = None,
            state_value: bool | None = None):
        self.__device_class = device_class
        self.__state_value = state_value
    
    @property
    def data(self):
        if self.__device_class is not None:
            return {f"binary_sensor__{self.__device_class}": self.__state_value}
        else:
            return {f"binary_sensor": self.__state_value}