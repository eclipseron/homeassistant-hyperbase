class LightColumns:
    def __init__(self):
        self._columns = {
            "light_brightness": {"kind": "int", "required": False},
            "light_color_temp_kelvin": {"kind": "int", "required": False},
            "light_hue": {"kind": "double", "required": False},
            "light_saturation": {"kind": "double", "required": False},
            "light_is_on": {"kind": "boolean", "required": False},
            "light_color_temp": {"kind": "int", "required": False},
            "light_red": {"kind": "int", "required": False},
            "light_green": {"kind": "int", "required": False},
            "light_blue": {"kind": "int", "required": False},
            "light_x_color": {"kind": "double", "required": False},
            "light_y_color": {"kind": "double", "required": False},
        }
    
    @property
    def schema(self):
        return self._columns


class LightEntityData:
    def __init__(self,
        state_value: bool | None = None,
        brightness: int | None = None,
        color_temp_kelvin: int | None = None,
        hue: float | None = None,
        saturation: float | None = None,
        color_temp: int | None = None,
        red: int | None = None,
        green: int | None = None,
        blue: int | None = None,
        x_color: float | None = None,
        y_color: float | None = None
        ):
        self._state_value = state_value
        self._brightness = brightness
        self._color_temp_kelvin = color_temp_kelvin
        self._hue = hue
        self._saturation = saturation
        self._color_temp = color_temp
        self._red = red
        self._green = green
        self._blue = blue
        self._x_color = x_color
        self._y_color = y_color
    
    @property
    def data(self):
        return {
            "light_brightness": self._brightness,
            "light_color_temp_kelvin": self._color_temp_kelvin,
            "light_hue": self._hue,
            "light_saturation": self._saturation,
            "light_is_on": self._state_value,
            "light_color_temp": self._color_temp,
            "light_red": self._red,
            "light_green": self._green,
            "light_blue": self._blue,
            "light_x_color": self._x_color,
            "light_y_color": self._y_color,
        }