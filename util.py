from re import sub

def format_device_name(device_name: str):
    _name = device_name.lower()
    _name = sub(r'[^\w\s]', '', _name) # remove non alphanumeric characters
    _name = sub(r'\s+', '_', _name) # replace whitespaces with underscore
    return _name