class VacuumColumns:
    def __init__(self):
        self.__columns = {
            "vacuum_fan_speed": {"kind": "string", "required": False},
            "vacuum_status": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class VacuumEntityData:
    def __init__(self,
        vacuum_fan_speed: str | None = None,
        vacuum_status: str | None = None,
        ):
        self._vacuum_fan_speed = vacuum_fan_speed
        self._vacuum_status = vacuum_status
    
    @property
    def data(self):
        return {
            "vacuum_fan_speed": self._vacuum_fan_speed,
            "vacuum_status": self._vacuum_status,
        }