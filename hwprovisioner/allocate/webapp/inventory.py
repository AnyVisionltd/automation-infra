"""
logic for managing the inventory

./api/inventory
"""
from aiohttp import web


async def get_all():
    """
    retrieves all available assets in the inventory
    """
    return web.json_response(
        {
            "status": 200,
            "data": [
                {
                    "inventory_id": "8a526e72-bcde-45e6-8a5f-f598b350f093",
                    "labels": ["nvidia"],
                    "cpu_count": 10,
                    "memory_count": 16,
                    "gpus": ["nvidia"],
                    "type": "foo",
                }
            ]
        },
        content_type="application/json",
        headers={},
    )


async def get_one(inventory_id):
    """
    retrieves a single asset from the inventory
    """
    return web.json_response(
        {
            "status": 200,
            "data": {
                "inventory_id": inventory_id,
                "labels": ["nvidia"],
                "cpu_count": 10,
                "memory_count": 16,
                "gpus": ["nvidia"],
                "type": "foo",
            }
        },
        content_type="application/json",
        headers={},
    )
