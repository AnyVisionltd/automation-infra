"""
logic for trying to lock a resource
"""
from aiohttp import web

from webapp.responses import message, error


class LockView(web.View):
    """
    presentation and business logic for locking resources
    """

    async def post(self):
        """
        ---
        description: responsible for changing the state of a lock/reservation
        tags:
          - Lock
        produces:
          - application/json
        parameters:
          - in: body
            name: json payload
            required: true
            description: the name of the resource you would like to reserve
            schema:
              type: object
              required:
                - alias
              properties:
                alias:
                  type: string
                  example: libvirt_vagrant
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
                    alias:
                      type: string
                      description: the alias of the host. this will be the same
                                   as the string which was sent in the request
                      example: libvirt_vagrant
                    connection:
                      type: object
                      description: connection details for the resource
                      properties:
                        username:
                          type: string
                          description: the username for connecting to the
                                       device
                          example: patrick
                        password:
                          type: string
                          description: the password for connecting to the
                                       device
                          example: ""
                        key_file_path:
                          type: string
                          description: the key_file_path for connecting to the
                                       device
                          example: ~/.vagrant.d/insecure_private_key
                        address:
                          type: string
                          description: the address for connecting to the
                                       device
                          example: 192.168.99.99
                        host_type:
                          type: string
                          description: the host_type of the target device
                          example: virtual
                    heartbeat:
                      type: object
                      description: information about the heartbeat
                      properties:
                        url:
                          type: string
                          description: the url to send heartbeats against
                          example: http://keepalive/api/v1/renew/${alias}/
                        timeout:
                          type: integer
                          description: the frequency (in seconds) for which you
                                       should call the heartbeat
                          example: 20
                        documentation:
                          type: string
                          description: the url for this api's documentation
                          example: http://keepalive/api/v1/doc/renew/
          "410":
            description: resource not currently available (already locked)
          "404":
            description: alias not recognised
          "405":
            description: method not allowed
        """
        jjson = await self.request.json()
        try:
            self.__validate(jjson)
        except ValueError as err:
            return error(msg=str(err), status=403)
        return message(
            msg="""
            // this would be an object reflecting details for {} //
            """.format(
                jjson.get("alias")
            )
        )

    @staticmethod
    def __validate(data):
        """
        validates the lock payload
        """
        required = ["alias"]
        for field in required:
            if field not in data:
                raise ValueError("payload must include '{}'".format(field))
            if data[field] == "":
                raise ValueError("'{}' must not be empty".format(field))
