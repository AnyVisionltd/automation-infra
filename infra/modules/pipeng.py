import grpc
from munch import Munch
import sshtunnel
import CONSTS
from infra.model import plugins
import common_pb2
import image_processing_pb2
import pipe_ng_service_pb2_grpc


class PipeNg(object):
    # TODO: I need to support multiple pipes..
    # Do I need to detect them automaticall?
    def __init__(self, host=Munch(ip='0.0.0.0', user='user', password='user1!')):
        self._host = host
        self._tunnel = sshtunnel.open_tunnel(host.ip,
                                             ssh_username=host.user, ssh_password=host.password,
                                             remote_bind_address=(CONSTS.PIPENG, CONSTS.PIPENG_PORT))
        self._tunnel.start()
        self._channel = None

    @property
    def channel(self):
        if self._channel is None:
            self._channel = self.create_channel()
        return self._channel

    def create_channel(self):
        return grpc.insecure_channel(f'localhost:{self._tunnel.local_bind_port}')

    def get_features(self, image_path):
        # TODO: do some type of image_path parsing..
        # if image_path.startswith('http'):
        #     image_path.replace('http://' + sw_host + ':' + sw_port + '/buckets/', 's3://')
        #     pipe_ng_path = 's3:///buckets/'
        request = image_processing_pb2.Request(type=common_pb2.FACE, image=[image_path])
        stub = pipe_ng_service_pb2_grpc.IPCStub(self.channel)
        response = stub.ProcessImage(request)
        return response


plugins.register('PipeNg', PipeNg)
