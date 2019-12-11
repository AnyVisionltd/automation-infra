"""
logic for managing the inventory
"""
from aiohttp import web

from webapp.responses import message


class InventoryView(web.View):
    """
    presentation and business logic for managing resources
    """

    async def get(self):
        """
        ---
        description: lists all of the items in the inventory
        tags:
          - Inventory
        produces:
          - application/json
        responses:
          "200":
            description: successful operation.
            schema:
              type: object
              properties:
                status:
                  type: integer
                  description: the status of the request
                  example: 200
                data:
                  type: object
                  description: all of the resource data
                  properties:
                    inventory:
                      type: array
                      description: the alias of the host. this will be the same
                                   as the string which was sent in the request
                      items:
                        type: object
                        properties:
                          alias:
                            type: string
                            description: the alias of this resource
                            example: libvirt_vagrant
                          host_type:
                            type: string
                            description: the host type
                            example: virtual
                          address:
                            type: string
                            description: the address for this resource
                            example: 192.168.99.99
          "423":
            description: resource not currently available (already locked)
          "404":
            description: alias not recognised
        """
        return self.__allitems()

    @staticmethod
    def __allitems():
        """
        returns all inventory items
        """
        return message(msg="all items")
