import requests
import sshtunnel
from PIL import Image
from io import BytesIO

import CONSTS
from infra.model import plugins


class Seaweed(object):
    def __init__(self, host, sw_host=CONSTS.SEAWEED, sw_port=CONSTS.SEAWEED_PORT):
        # self._host = host
        # self._sw_host = sw_host
        # self._sw_port = sw_port
        self._sw_path_prefix = f'http://{sw_host}:{sw_port}'
        self.tunnel = sshtunnel.open_tunnel(host.ip,
                                   ssh_username=host.user, ssh_password=host.password,
                                   remote_bind_address=(sw_host, sw_port))
        self.tunnel.start()

    def get_full_seaweed_path(self, relative_path):
        full_sw_path = f'http://localhost:{self.tunnel.local_bind_port}/{relative_path}'
        return full_sw_path

    def get_image(self, relative_path):
        full_sw_path = self.get_full_seaweed_path(relative_path)
        print(f"sw_path: {full_sw_path}")
        res = requests.get(full_sw_path)
        # img = Image.open(BytesIO(res.content))
        # img.show()
        return res

    # TODO: implement other methods here...


plugins.register('Seaweed', Seaweed)
