import logging
import time

from automation_infra.utils.timer import timeit

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
    """Every plugin should implement 3 methods:
    ping - verifies service is up and running and plugin is communicating with it properly
    reset_state - resets state of service back to origin, before tests ran
    verify_functionality - a method which does basic 'sanity' test flow of plugin methods and verifies plugin is
    functioning properly... Useful to run after making changes to a plugin, or when seeing weird plugin behavior
    """
    logging.info(f"cleaning plugin {plugin}")
    with timeit(f"clean {plugin}"):
        try:
            plugin.ping()
        except AttributeError:
            logging.debug(f"plugin {plugin} doesnt have ping method")
        except Exception as e:
            raise Exception(f"Clean between tests failed on {plugin} plugin, {e}")
            exit(1)
        try:
            plugin.reset_state()
        except AttributeError:
            logging.debug(f"plugin {plugin} doesnt have reset_state method")
        try:
            plugin.ping()
        except AttributeError:
            logging.debug(f"plugin {plugin} doesnt have ping method")
        except Exception as e:
            raise Exception(f"Clean between tests failed on {plugin} plugin, {e}")
            exit(1)
    logging.info(f"done cleaning plugin {plugin}")
