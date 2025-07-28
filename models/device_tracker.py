from typing import Any

class DeviceTrackerColumns:
    def __init__(self):
        self.__columns = {
            "device_tracker_battery": {"kind": "integer", "required": False},
            "device_tracker_is_connected": {"kind": "boolean", "required": False},
            "device_tracker_latitude": {"kind": "double", "required": False},
            "device_tracker_longitude": {"kind": "double", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class DeviceTrackerEntityData:
    def __init__(self,
        device_tracker_battery: int | None = None,
        device_tracker_is_connected: bool | None = None, 
        device_tracker_latitude: float | None = None, 
        device_tracker_longitude: float | None = None, 
        ):
        self._device_tracker_battery = device_tracker_battery
        self._device_tracker_is_connected = device_tracker_is_connected
        self._device_tracker_latitude = device_tracker_latitude
        self._device_tracker_longitude = device_tracker_longitude
    
    @property
    def data(self):
        return {
            "device_tracker_battery": self._device_tracker_battery,
            "device_tracker_is_connected": self._device_tracker_is_connected,
            "device_tracker_latitude": self._device_tracker_latitude,
            "device_tracker_longitude": self._device_tracker_longitude,
        }