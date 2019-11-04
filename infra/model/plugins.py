plugins = {}


def register(name, klass):
    """
    Please register your plugins using this function
    the klass will receive the Host object to it constructor,
    and will be cached while the Host object exists
    """
    assert name not in plugins
    assert isinstance(name, str)
    plugins[name] = klass
