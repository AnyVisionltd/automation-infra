"""
logic for the healthcheck

./api/_healthcheck
"""
from aiohttp import web


async def get():
    """
    retrieves a single asset from the inventory
    """
    return web.json_response(
        {
            "status": 200,
            "data": "The service is functioning as expected",
        },
        content_type="application/json",
        headers={},
    )
