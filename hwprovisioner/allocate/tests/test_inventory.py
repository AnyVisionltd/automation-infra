"""
ensure the inventory method contracts are unchanged
"""
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop

from webapp import app
from webapp import inventory


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
            "data": {},
        }
        assert expected == result

    @unittest_run_loop
    async def test_post_invaliddata(self):
        """
        invalid data supplied for POST to ./api/inventory/
        """
        resp = await self.client.request(
            "POST", "/api/inventory/", data={"data": {}},
        )
        result = await resp.json()
        expected = {"errors": "post 'data' seems to be an invalid type"}

        assert resp.status == 200
        assert result == expected

    @unittest_run_loop
    async def test_post(self):
        """
        happy-path for adding a new item to ./api/inventory/
        """
        resp = await self.client.request(
            "POST",
            "/api/inventory/",
            json={
                "data": {
                    "labels": ["foo", "bar"],
                    "cpu_count": 1,
                    "memory_count": 4,
                    "gpus": ["x", "y"],
                    "type": "foo",
                }
            },
        )
        result = await resp.json()
        expected = {
            "status": 301,
            "data": {
                "cpu_count": 10,
                "gpus": ["nvidia"],
                "inventory_id": "dummy-item",
                "labels": ["x"],
                "memory_count": 16,
                "type": "foo",
            },
        }
        assert expected == result

    @staticmethod
    def test_post_validation_invalidtype():
        """
        ensure the validation is catching known invalidtype
        """
        expected = b'{"errors": "post \'data\' seems to be an invalid type"}'
        resp = inventory.post({})
        assert resp.body == expected

    @staticmethod
    def test_post_validation_missingfields():
        """
        ensure we let the user know that some fields are missing
        """
        expected = b'{"errors": ["You must provide a cpu_count >= 1", "You must provide a memory_count >= 1", "You must provide a type"]}'
        resp = inventory.post({"data": {"labels": ["x"]}})
        assert resp.body == expected

    @staticmethod
    def test_post_validation_cpucountmin():
        """
        cpu_count can not be < 1
        """
        expected = b'{"errors": ["You must provide a cpu_count >= 1"]}'
        resp = inventory.post(
            {
                "data": {
                    "labels": ["x"],
                    "cpu_count": 0,
                    "memory_count": 1,
                    "type": "x",
                }
            }
        )
        assert resp.body == expected

    @staticmethod
    def test_post_validation_memorycountmin():
        """
        memory count can not be < 1
        """
        expected = b'{"errors": ["You must provide a memory_count >= 1"]}'
        resp = inventory.post(
            {
                "data": {
                    "labels": ["x"],
                    "cpu_count": 1,
                    "memory_count": 0,
                    "type": "x",
                }
            }
        )
        assert resp.body == expected

    @staticmethod
    def test_post_validation_type():
        """
        type can not be ''
        """
        expected = b'{"errors": ["You must provide a type"]}'
        resp = inventory.post(
            {
                "data": {
                    "labels": ["x"],
                    "cpu_count": 1,
                    "memory_count": 1,
                    "type": "",
                }
            }
        )
        assert resp.body == expected
