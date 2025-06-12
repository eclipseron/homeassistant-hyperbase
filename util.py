from re import sub, fullmatch

from .exceptions import InvalidConnectorEntity

def format_device_name(device_name: str):
    _name = device_name.lower()
    _name = sub(r'[^\w\s]', '', _name) # remove non alphanumeric characters
    _name = sub(r'\s+', '_', _name) # replace whitespaces with underscore
    return _name


def is_valid_connector_entity(user_input: str) -> str:
    """
    Checks if the input is valid based on the following rules:
    - Only alphanumeric characters allowed
    - Hyphens (-) and underscores (_) are allowed
    - No whitespace or other special characters
    """
    pattern = r'^[A-Za-z0-9_-]+$'
    is_valid = bool(fullmatch(pattern, user_input))
    if not is_valid:
        raise InvalidConnectorEntity
    return user_input