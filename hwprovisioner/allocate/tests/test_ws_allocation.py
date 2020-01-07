"""
ensure the allocation websocket contracts are unchanged
"""
from webapp import app


async def test_get_ws(aiohttp_client):
    """
    happy-path for inventory get /
    expectation: normal response
    """
    application = app.run_app(run=False)
    client = await aiohttp_client(application)
    websocket = await client.ws_connect("/api/allocate/")
    message = {"message": "hi"}
    await websocket.send_json(message)
    reply = await websocket.receive_json()
    assert reply == {"status": "connected"}
    assert websocket.closed is False
