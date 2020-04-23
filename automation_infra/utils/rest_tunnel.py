import requests


class RestTunnel(object):
    def __init__(self, local_bind_port):
        self.port = local_bind_port

    def build_url(self, route):
        url = f"http://localhost:{self.local_bind_port}{route}"
        return url

    def get(self, route, params):
        """route is the path of the url without the domainname"""
        formatted_url = self.build_url(route)
        requests.get(formatted_url, params=params)

    def post(self, url, params):
        pass

    def put(self, url, params):
        pass
