from abc import ABC, abstractmethod
import requests


class HTTPRequestor():
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

