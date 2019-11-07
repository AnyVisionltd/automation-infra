import requests
import sshtunnel
from PIL import Image
from io import BytesIO

import CONSTS
from infra.model import plugins


class Seaweed(object):
    def __init__(self, host):
        self.tunnel = sshtunnel.open_tunnel(host.ip,
                                   ssh_username=host.user, ssh_password=host.password,
                                   remote_bind_address=(CONSTS.SEAWEED, CONSTS.SEAWEED_PORT))
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
