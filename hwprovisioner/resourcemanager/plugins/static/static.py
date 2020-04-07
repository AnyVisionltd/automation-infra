"""
static resource manager plugin

this plugin handles statically defined resources in the resources.yml
"""
from plugins.plugin import ResourceManagerPlugin


class StaticPlugin(ResourceManagerPlugin):
    """
    all of the methods required for handling static resources
    """
    def __init__(self, rtype, rref, data):
        """
        instantiate global vars
        """
        ResourceManagerPlugin.__init__(self, rtype, rref, data)

    async def readyup(self):
        """
        There's nothing to do here for static resources
        """
        return self.job_data

    async def teardown(self):
        """
        There's nothing to do here for static resources
        """
        return True
