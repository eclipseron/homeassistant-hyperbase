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
    