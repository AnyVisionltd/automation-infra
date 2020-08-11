from abc import ABC, abstractmethod
import requests


class HTTPRequestor(object):
    """The goal of the requestor object is to enable communication with a service in different ways.
    The requestor needs to implement the CRUD methods.
    Then the use would be as follows:
    req = Requestor()
    service = Service(req)
    res = service.method()

    where Service is defined something like:
    def Service(requestor):
        def __init__():
            self.requestor = requestor

        def method():
            route = '/path/to/route'
            res = self.requestor.get(route)
            return res

    The automation-infra implemented TunnelRequestor which enables interacting with a service via existing tunnel.
    Other potential requestor could be a KongRequestor (to be implemented) or others as the need arises."""

    @abstractmethod
    def get(self, route, params=None, **kwargs) -> requests.Response:
        """route is the path of the url without the domainname"""
        pass

    @abstractmethod
    def post(self, route, data=None, json=None, **kwargs) -> requests.Response:
        pass

    @abstractmethod
    def put(self, route, data=None, **kwargs) -> requests.Response:
        pass

    @abstractmethod
    def delete(self, route, **kwargs) -> requests.Response:
        pass

    @abstractmethod
    def patch(self, url, data=None, **kwargs) -> requests.Response:
        pass


class SimpleRequestor(HTTPRequestor):

    def __init__(self, base_uri, verify_cert=False):
        self.base_uri = base_uri
        self.verify_cert = verify_cert

    def build_url(self, route):
        url = f"{self.base_uri}{route}"
        return url

    def get(self, route, params=None, **kwargs) -> requests.Response:
        """route is the path of the url without the domainname"""
        return requests.get(self.build_url(route), params, verify=self.verify_cert, **kwargs)

    def post(self, route, data=None, json=None, **kwargs) -> requests.Response:
        return requests.post(self.build_url(route), data, json, verify=self.verify_cert, **kwargs)

    def put(self, route, data=None, **kwargs) -> requests.Response:
        return requests.put(self.build_url(route), route, data, verify=self.verify_cert, **kwargs)

    def delete(self, route, **kwargs) -> requests.Response:
        return requests.delete(self.build_url(route), route, verify=self.verify_cert, **kwargs)

    def patch(self, route, data=None, **kwargs) -> requests.Response:
        return requests.patch(self.build_url(route), data, verify=self.verify_cert, **kwargs)

