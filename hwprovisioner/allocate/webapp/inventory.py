"""
logic for managing the inventory

./api/inventory
"""
from aiohttp import web

from .exceptions import AllocateServerError, AllocateValidationError
from .responses import server_errors, validation_errors


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
            ],
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
            },
        },
        content_type="application/json",
        headers={},
    )


def post(body):
    """
    stores an inventory item
    """
    data = body.get("data")
    try:
        __insert(data)
    except AllocateServerError as err:
        return server_errors(err)
    except AllocateValidationError as err:
        return validation_errors(err)

    return web.json_response(
        {
            "status": 301,
            "data": {
                "inventory_id": "dummy-item",
                "labels": ["x"],
                "cpu_count": 10,
                "memory_count": 16,
                "gpus": ["nvidia"],
                "type": "foo",
            },
        },
        content_type="application/json",
        headers={},
    )


def __validate_post(data):
    """
    validates the input for inserting an inventory item
    """
    if not data:
        raise AllocateValidationError("post 'data' seems to be an invalid type")
    errors = []
    # labels
    if data.get("labels") is None or len(data.get("labels")) == 0:
        errors.append("You must provide labels")
    # cpu
    if (
        data.get("cpu_count") is None
        or int(data.get("cpu_count")) < 1
        or not isinstance(data.get("cpu_count"), int)
    ):
        errors.append("You must provide a cpu_count >= 1")
    # memory
    if (
        data.get("memory_count") is None
        or int(data.get("memory_count")) < 1
        or not isinstance(data.get("memory_count"), int)
    ):
        errors.append("You must provide a memory_count >= 1")
    # type
    if data.get("type") is None or data.get("type") == "":
        errors.append("You must provide a type")

    # fyi: no gpu validation considered for now

    if len(errors) != 0:
        raise AllocateValidationError(errors)


def __insert(data):
    """
    validates and then inserts an item to storage
    """
    try:
        __validate_post(data)
    except AllocateValidationError as err:
        raise err
