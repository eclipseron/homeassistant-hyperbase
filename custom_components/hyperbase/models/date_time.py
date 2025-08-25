class DateTimeColumns:
    def __init__(self):
        self.__columns = {
            "datetime": {"kind": "string", "required": False},
        }
    @property
    def schema(self):
        return self.__columns


class DateTimeEntityData:
    def __init__(self, datetime_iso: str | None = None):
        self.__state_value = datetime_iso
    
    @property
    def data(self):
        return {"datetime": self.__state_value}