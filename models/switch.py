from .base import BASE_COLUMNS, BaseModel



SWITCH_COLUMNS = {
    **BASE_COLUMNS,
    "device_class": {"kind": "string", "required": False},
    "is_on": {"kind": "boolean", "required": False},
}


class SwitchColumns:
    def __init__(self, device_classes):
        self.__columns = {}
        for dc in device_classes:
            self.__columns[f"switch__{dc}"] = {"kind": "boolean", "required": False}
    @property
    def schema(self):
        return self.__columns

class SwitchModel(BaseModel):
    """asdasd"""