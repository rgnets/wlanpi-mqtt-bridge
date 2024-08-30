import subprocess


def get_full_class_name(obj: object) -> str:
    """
    Gets the full class name and path of an object for use in errors.
    :param obj: The object to get the name and path of
    :return: The full name and path as a string.
    """
    module = obj.__class__.__module__
    if module is None or module == str.__class__.__module__:
        return obj.__class__.__name__
    return module + "." + obj.__class__.__name__


def get_default_gateways() -> dict[str, str]:
    # Execute 'ip route show' command which lists all network routes
    cmd = "ip route show"
    output = subprocess.check_output(cmd, shell=True).decode("utf-8").split("\n")

    gateways: dict[str, str] = {}
    for line in output:
        if "default via" in line:  # This is the default gateway line
            res = line.split("via ")[1].split(" dev ")
            gateways[res[1].strip()] = res[0].strip()
    return gateways
