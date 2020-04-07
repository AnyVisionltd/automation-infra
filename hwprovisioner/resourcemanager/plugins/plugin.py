"""
This file acts as bridge between the resource manager and it's plugins. The
idea here is that resource manager plugins will inherit this class and as
such will conform to an API that the resource manager understands
"""
from abc import ABC, abstractmethod

from webapp.config import CONFIG
from webapp.settings import log


class ResourceManagerPlugin(ABC):
    """
    ResourceManagerPlugin - the parent class for resource manager plugins
    This is instantiated per allocation, so the state in each object relates
    to a single job
    """
    def __init__(self, rtype, rref, data):
        """
        populate globals
        """
        self.resource_type = rtype
        self.resource_name = rref
        self.resourcemanager_id = CONFIG["UUID"]
        self.job_data = data
        self.log = log

    @abstractmethod
    def readyup(self):
        """
        how should we create the resource?
        """

    @abstractmethod
    def teardown(self):
        """
        how should we tear this resource down?
        """
