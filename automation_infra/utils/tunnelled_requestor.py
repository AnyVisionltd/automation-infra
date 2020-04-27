import requests

from automation_infra.utils.httprequestor import HTTPRequestor


class TunnelledRequestor(HTTPRequestor):
    """The goal of the requestor object is to enable communication with a service in different ways.
    This requestor enables interacting with a service via an existing tunnel.
    Other possible requestors are Kong requestor (to use for interacting with a service via kong),
    or others as the need arises."""

    def __init__(self, tunnel):
        """params: tunnel: infra.model.Tunnel object
                    A tunnel can be started with the help of the host.TunnelManager plugin start_tunnel() method"""
        self.tunnel = tunnel

    def build_url(self, route):
        url = f"http://{self.tunnel._hostname}:{self.tunnel._local_bind_port}{route}"
        return url

    def get(self, route, params=None, **kwargs):
        """route is the path of the url without the domainname"""
        formatted_url = self.build_url(route)
        res = requests.get(formatted_url, params=params, **kwargs)
        return res

    def post(self, route, data=None, json=None, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.post(formatted_url, data, json, **kwargs)
        return res

    def put(self, route, data=None, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.put(formatted_url, data, **kwargs)
        return res

    def delete(self, route, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.delete(formatted_url, **kwargs)
        return res

    # TODO: implement other CRUD methods if needed...
