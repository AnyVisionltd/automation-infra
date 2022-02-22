import requests

from automation_infra.utils.httprequestor import HTTPRequestor


class KongRequestor(HTTPRequestor):
    """The goal of the requestor object is to enable communication with a service in different ways.
    This requestor enables interacting with a service via an existing tunnel.
    Other possible requestors are Kong requestor (to use for interacting with a service via kong),
    or others as the need arises."""

    def __init__(self, hostname, username, password, suffix='/'):
        """params: tunnel: infra.model.Tunnel object
                    A tunnel can be started with the help of the host.TunnelManager plugin start_tunnel() method"""
        self.hostname = hostname
        self.bearer_token = None
        self.username = username
        self.password = password
        self.suffix = suffix
        self._login()


    def _login(self, params=None, **kwargs):
        import pdb; pdb.set_trace()
        formatted_url = self.build_url('login')
        formatted_url = ''.join(formatted_url.split('/api'))
        payload = {'username': self.username, 'password': self.password}
        headers = {'content-type': 'application/json'}
        res = requests.post(formatted_url, payload=payload, headers=headers, verify=False)


    def build_url(self, route):
        url = f"https://{self.hostname}/{self.suffix}api/{route}"
        return url

    def get(self, route, params=None, verify=False, **kwargs, ):
        """route is the path of the url without the domainname"""
        formatted_url = self.build_url(route)
        res = requests.get(formatted_url, params=params, **kwargs)
        return res

    def post(self, route, data=None, json=None, verify=False, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.post(formatted_url, data, json, **kwargs)
        return res

    def put(self, route, data=None, verify=False, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.put(formatted_url, data, **kwargs)
        return res

    def delete(self, route, verify=False, **kwargs):
        formatted_url = self.build_url(route)
        res = requests.delete(formatted_url, **kwargs)
        return res

    def patch(self, route, data=None, verify=False, **kwargs) -> requests.Response:
        formatted_url = self.build_url(route)
        res = requests.patch(formatted_url, data, **kwargs)
        return res

    # TODO: implement other CRUD methods if needed...
