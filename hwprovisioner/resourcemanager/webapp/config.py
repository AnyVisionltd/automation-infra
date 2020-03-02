"""
service configuration
"""
import os
import sys
import uuid
import yaml

from .settings import log


def load_config(configfile):
    """
    attempt to load config 
    """
    log.debug("loading config")
    try:
        with open(configfile, "r") as yml:
            config = yaml.load(yml, Loader=yaml.FullLoader)
            # allocate rest api location (separate service)
            config["ALLOCATE_API"] = os.getenv(
                "ALLOCATE_API", "http://localhost:8080/api/"
            )
            # on-disk uuid path. an identifier used for the allocation queues
            config["UUID_PATH"] = os.getenv(
                "UUID_PATH", "./.my-uuid"
            )
            config["UUID"] = __uuid(config["UUID_PATH"])
        return config
    except EnvironmentError:
        print("Failed to load config at %s" % configfile)
        sys.exit(1)


def __uuid(path):
    """
    if a uuid for this service does not yet exist it will be created (stored
    on disk). returns the uuid
    """
    log.debug("getting uuid")
    if not os.path.exists(path):
        log.debug("uuid doesnt exist. creating it")
        with open(path, "w") as ufile:
            uid = str(uuid.uuid4())
            log.debug(uid)
            ufile.write(uid)
    with open(path, "r") as uid:
        log.debug("uuid exists. returning it")
        return uid.read()


CONFIG = load_config(os.getenv("CONFIG_FILE", "resources.yml"))
