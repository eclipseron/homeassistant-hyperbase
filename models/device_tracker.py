from typing import Any

class DeviceTrackerColumns:
    def __init__(self):
        self.__columns = {
            "device_tracker_battery": {"kind": "integer", "required": False},
            "device_tracker_latitude": {"kind": "double", "required": False},
            "device_tracker_longitude": {"kind": "double", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class DeviceTrackerEntityData:
    def __init__(self,
        battery: int | None = None,
        latitude: float | None = None, 
        longitude: float | None = None, 
        ):
        self._battery = battery
        self._latitude = latitude
        self._longitude = longitude
    
    @property
    def data(self):
        return {
            "device_tracker_battery": self._battery,
            "device_tracker_is_connected": self._is_connected,
            "device_tracker_latitude": self._latitude,
            "device_tracker_longitude": self._longitude,
        }