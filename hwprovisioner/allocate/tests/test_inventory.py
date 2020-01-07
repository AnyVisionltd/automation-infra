"""
ensure the inventory method contracts are unchanged
"""
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from webapp import app


class TestInventory(AioHTTPTestCase):
    """
    Runs over all success and failure scenarios for the inventory endpoints
    """

    async def get_application(self):
        return app.run_app(run=False)

    @unittest_run_loop
    async def test_get_all(self):
        """
        happy-path for ./api/inventory
        """
        resp = await self.client.request("GET", "/api/inventory")
        assert resp.status == 200
        result = await resp.json()
        expected = {
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
        }
        assert expected == result

    @unittest_run_loop
    async def test_get_one(self):
        """
        happy-path for ./api/inventory/{inventory_id}
        """
        resp = await self.client.request("GET", "/api/inventory/123")
        assert resp.status == 200
        result = await resp.json()
        expected = {
            "status": 200,
            "data": {
                "inventory_id": "123",
                "labels": ["nvidia"],
                "cpu_count": 10,
                "memory_count": 16,
                "gpus": ["nvidia"],
                "type": "foo",
            },
        }
        assert expected == result

    @unittest_run_loop
    async def test_get_one_invalidinput(self):
        """
        invalid input ./api/inventory/{inventory_id}
        """
        resp = await self.client.request("GET", "/api/inventory/a")
        assert resp.status == 400  # bad request

    @unittest_run_loop
    async def test_get_one_notfound(self):
        """
        missing item ./api/inventory/{inventory_id}
        """
        resp = await self.client.request("GET", "/api/inventory/0")
        assert resp.status == 200
        result = await resp.json()
        expected = {
            "status": 404,
            "data": {
            },
        }
        assert expected == result
