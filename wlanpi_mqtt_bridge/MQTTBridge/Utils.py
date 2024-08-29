def get_full_class_name(obj):
    """
    Gets the full class name and path of an object for use in errors.
    :param obj: The object to get the name and path of
    :return: The full name and path as a string.
    """
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + "." + obj.__class__.__name__
