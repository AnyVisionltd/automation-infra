import logging

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


def clean(plugin):
    try:
        assert plugin.ping()
    except AttributeError:
        logging.debug(f"plugin {plugin} doesnt have ping method")
    except ConnectionError:
        raise (f"Clean between tests failed on {plugin} plugin")
        exit(1)
    try:
        assert plugin.reset_state()
    except AttributeError:
        logging.debug(f"plugin {plugin} doesnt have reset_state method")
    try:
        assert plugin.verify_functionality()
    except AttributeError:
        logging.debug(f"plugin {plugin} doesnt have verify_functionality method")
