class TimeColumns:
    def __init__(self):
        self.__columns = {
            "date": {"kind": "timestamp", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class TimeEntityData:
    def __init__(self, time_iso: str | None = None):
        self.__state_value = time_iso
    
    @property
    def data(self):
        return {"date": self.__state_value}