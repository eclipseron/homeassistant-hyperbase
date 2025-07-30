class CameraColumns:
    def __init__(self):
        self.__columns = {
            "camera": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class CameraEntityData:
    def __init__(self, state_value: str | None = None):
        self.__state_value = state_value
    
    @property
    def data(self):
        return {"camera": self.__state_value}