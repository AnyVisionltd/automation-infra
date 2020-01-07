"""
a library of helper methods for responding to requests in a standardised format
"""
from aiohttp.web import json_response


def validation_errors(messages):
    """
    The user has encountered some errors - convert these into json
    """
    msg = {"errors": messages.errors}
    return json_response(msg)


def server_errors(messages):
    """
    The server has encountered some errors - convert these into json
    """
    msg = {"server_errors": messages.errors}
    return json_response(msg, status=500)
