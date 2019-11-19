import requests
import sshtunnel
from munch import Munch

from infra.model import plugins
from runner import CONSTS


class CameraService(object):
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self._tunnel = sshtunnel.open_tunnel(host.ip,
                                             ssh_username=host.user, ssh_password=host.password, ssh_pkey=host.keyfile,
                                             remote_bind_address=(CONSTS.CAMERA_SERVICE, CONSTS.CAMERA_SERVICE_PORT))
        self._tunnel.start()

    def get_cameras(self):
        res = requests.get(f'http://localhost:{self._tunnel.local_bind_port}/cameras')
        assert res.status_code == 200
        return res


plugins.register('CameraService', CameraService)
