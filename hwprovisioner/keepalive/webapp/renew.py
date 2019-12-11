"""
logic for extending the lease on a resource
"""
from aiohttp import web

from webapp.responses import message


class RenewView(web.View):
    """
    presentation and business logic for renewing resource leases
    """

    async def put(self):
        """
        ---
        description: extends the lease on a resource
        tags:
          - Renew
        produces:
          - application/json
        parameters:
          - in: path
            name: alias
            description: the name of the resource you would like to renew a
                         lease upon
            default: libvirt_vagrant
          - in: path
            name: lockhash
            description: a hash thats unique to a given resource reservation
            default: 823e4567-e89b-12d3-a456-426655440008
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
                    expires:
                      type: string
                      description: the alias of the host. this will be the same
                                   as the string which was sent in the request
                      example: 102870147
          "410":
            description: resource is not currently locked
          "404":
            description: alias not recognised
          "405":
            description: method not allowed
          "403":
            description: lockhash not valid
        """
        return message(
            msg="""
            // this would be an object reflecting details for {} //
            """.format(
                self.request.match_info["alias"]
            )
        )
