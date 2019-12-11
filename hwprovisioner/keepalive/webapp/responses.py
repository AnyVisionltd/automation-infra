"""
contains the rendering methods for this service
"""
from aiohttp import web


CONTENT_TYPE = "application/json"


def message(msg, status=200):
    """
    render a message
    """
    return web.json_response(
        {"data": msg, "status": status}, content_type=CONTENT_TYPE
    )


def error(msg, status):
    """
    render a error message
    """
    msg = "Error: {}".format(msg)
    return message(msg, status)
