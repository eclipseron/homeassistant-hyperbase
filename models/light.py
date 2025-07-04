from typing import Any
from .base import BaseModel, BASE_COLUMNS


LIGHT_COLUMNS = {
    **BASE_COLUMNS,
    "brightness": {"kind": "int", "required": False},
    "color_mode": {"kind": "string", "required": False},
    "color_temp_kelvin": {"kind": "int", "required": False},
    "effect": {"kind": "string", "required": False},
    "hue": {"kind": "double", "required": False},
    "saturation": {"kind": "double", "required": False},
    "is_on": {"kind": "boolean", "required": False},
    "max_color_temp_kelvin": {"kind": "int", "required": False},
    "min_color_temp_kelvin": {"kind": "int", "required": False},
    "color_temp": {"kind": "int", "required": False},
    "red": {"kind": "int", "required": False},
    "green": {"kind": "int", "required": False},
    "blue": {"kind": "int", "required": False},
    # "white": {"kind": "int", "required": False},
    # "cool_white": {"kind": "int", "required": False},
    # "warm_white": {"kind": "int", "required": False},
    "x_color": {"kind": "int", "required": False},
    "y_color": {"kind": "int", "required": False},
}


class LightColumns:
    def __init__(self):
        self.__columns = {
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
        return self.__columns


class LightEntityData:
    def __init__(self,
        state_value: Any | None = None,
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
        self.__state_value = state_value
        self.__brightness = brightness
        self.__color_temp_kelvin = color_temp_kelvin
        self.__hue = hue
        self.__saturation = saturation
        self.__color_temp = color_temp
        self.__red = red
        self.__green = green
        self.__blue = blue
        self.__x_color = x_color
        self.__y_color = y_color
    
    @property
    def data(self):
        return {
            "light_brightness": self.__brightness,
            "light_color_temp_kelvin": self.__color_temp_kelvin,
            "light_hue": self.__hue,
            "light_saturation": self.__saturation,
            "light_is_on": self.__state_value == "on",
            "light_color_temp": self.__color_temp, 
            "light_red": self.__red,
            "light_green": self.__green,
            "light_blue": self.__blue,
            "light_x_color": self.__x_color,
            "light_y_color": self.__y_color,
        }


class LightModel():
    """asdad"""
    def __init__(self,
        base_info: BaseModel,
        brightness: str | None = None,
        color_mode: str | None = None,
        color_temp_kelvin: str | None = None,
        effect: str | None = None,
        hue: str | None = None,
        saturation: str | None = None,
        is_on: bool | None = None,
        max_color_temp_kelvin: str | None = None,
        min_color_temp_kelvin: str | None = None,
        color_temp: str | None = None,
        red: str | None = None,
        green: str | None = None,
        blue: str | None = None,
        # white: str | None = None,
        # cool_white: str | None = None,
        # warm_white: str | None = None,
        x_color: str | None = None,
        y_color: str | None = None,
    ):
        self.__data = {
            **base_info.base_data,
            "brightness": brightness,
            "color_mode": color_mode,
            "color_temp_kelvin": color_temp_kelvin, 
            "effect": effect, 
            "hue": hue,
            "saturation": saturation,
            "is_on": is_on,
            "max_color_temp_kelvin": max_color_temp_kelvin,
            "min_color_temp_kelvin": min_color_temp_kelvin, 
            "color_temp": color_temp, 
            "red": red,
            "green": green,
            "blue": blue,
            # "white": white,
            # "cool_white": cool_white,
            # "warm_white": warm_white,
            "x_color": x_color,
            "y_color": y_color,
        }
    
    @property
    def data(self):
        return self.__data
    