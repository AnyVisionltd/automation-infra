from munch import Munch
import requests
import sshtunnel

from runner import CONSTS
from infra.model import plugins


class Seaweed(object):
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self.tunnel = sshtunnel.open_tunnel(host.ip,
                                   ssh_username=host.user, ssh_password=host.password, ssh_pkey=host.keyfile,
                                   remote_bind_address=(CONSTS.SEAWEED, CONSTS.SEAWEED_PORT))
        self.tunnel.start()

    def get_full_seaweed_path(self, relative_path):
        full_sw_path = f'http://localhost:{self.tunnel.local_bind_port}/{relative_path}'
        return full_sw_path

    def get_image(self, relative_path):
        full_sw_path = self.get_full_seaweed_path(relative_path)
        print(f"sw_path: {full_sw_path}")
        res = requests.get(full_sw_path, timeout=10)
        # img = Image.open(BytesIO(res.content))
        # img.show()
        return res

    def get_buckets(self):
        res = requests.get(f'http://localhost:{self.tunnel.local_bind_port}/buckets')
        assert res.status_code == 200
        return res.content  # TODO: parse this into list or somn...

    def create_bucket(self, bucket_name):
        res = requests.put(f'http://localhost:{self.tunnel.local_bind_port}/buckets/{bucket_name}')
        assert res.status_code == 201

    def delete_bucket(self, bucket_name):
        res = requests.delete(f'http://localhost:{self.tunnel.local_bind_port}/buckets/{bucket_name}')
        assert res.status_code == 204

    # TODO: implement other methods here...



plugins.register('Seaweed', Seaweed)
