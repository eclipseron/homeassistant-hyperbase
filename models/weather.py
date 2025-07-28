class WeatherColumns:
    def __init__(self):
        self.__columns = {
            "weather_cloud_coverage": {"kind": "integer", "required": False},
            "weather_condition": {"kind": "string", "required": False},
            "weather_humidity": {"kind": "double", "required": False},
            "weather_feels_like_temperature": {"kind": "double", "required": False},
            "weather_dew_point": {"kind": "double", "required": False},
            "weather_pressure": {"kind": "double", "required": False},
            "weather_temperature": {"kind": "double", "required": False},
            "weather_visibility": {"kind": "double", "required": False},
            "weather_wind_gust_speed": {"kind": "double", "required": False},
            "weather_wind_speed": {"kind": "double", "required": False},
            "weather_ozone": {"kind": "double", "required": False},
            "weather_wind_bearing": {"kind": "string", "required": False},
        }

    @property
    def schema(self):
        return self.__columns


class WeatherEntityData:
    def __init__(self,
        cloud_coverage: int | None = None,
        condition: str | None = None,
        humidity: float | None = None,
        feels_like_temperature: float | None = None,
        dew_point: float | None = None,
        pressure: float | None = None,
        temperature: float | None = None,
        visibility: float | None = None,
        wind_gust_speed: float | None = None,
        wind_speed: float | None = None,
        ozone: float | None = None,
        wind_bearing: str | None = None,
        ):
        self._cloud_coverage = cloud_coverage
        self._condition = condition
        self._humidity = humidity
        self._feels_like_temperature = feels_like_temperature
        self._dew_point = dew_point
        self._pressure = pressure
        self._temperature = temperature
        self._visibility = visibility
        self._wind_gust_speed = wind_gust_speed
        self._wind_speed = wind_speed
        self._ozone = ozone
        self._wind_bearing = wind_bearing
    
    @property
    def data(self):
        return {
            "weather_cloud_coverage": self._cloud_coverage,
            "weather_condition": self._condition,
            "weather_humidity": self._humidity,
            "weather_feels_like_temperature": self._feels_like_temperature,
            "weather_dew_point": self._dew_point,
            "weather_pressure": self._pressure,
            "weather_temperature": self._temperature,
            "weather_visibility": self._visibility,
            "weather_wind_gust_speed": self._wind_gust_speed,
            "weather_wind_speed": self._wind_speed,
            "weather_ozone": self._ozone,
            "weather_wind_bearing": self._wind_bearing,
        }