"""
redis singleton
"""
import json
import os
import uuid

import redis
import asyncio_redis


# pylint: disable=R0903
class RedisClient:
    """
    exposes a redis connection
    """

    # pylint: disable=too-many-arguments
    def __init__(self, host, port, username, password, db=None):
        self._conn = None
        self._asyncconn = None
        self.host = host
        self.port = int(port)
        self.database = int(db)
        self.pool = redis.ConnectionPool(
            host=host, port=port, username=username, password=password, db=db
        )
        self._async = None

    @property
    def conn(self):
        """
        returns a redis connection
        """
        if not self._conn:
            self.__create_connection()
        return self._conn

    @property
    async def asyncconn(self):
        """
        return an async connection
        """
        if not self._asyncconn:
            await self.__create_asyncconnection()
        return self._asyncconn

    async def __create_asyncconnection(self):
        """
        instantiate an async connection
        """
        self._asyncconn = await asyncio_redis.Connection.create(
            host=self.host,
            port=self.port
        )

    def __create_connection(self):
        self._conn = redis.Redis(connection_pool=self.pool)

    async def resource_managers(self, resource_manager=None):
        conn = await self.asyncconn
        if resource_manager:
            res = await conn.hget("resource_managers", resource_manager)
            return json.loads(res)
        res = dict()
        resource_managers = await conn.hgetall_asdict("resource_managers")
        for name, resource_manager_str in resource_managers.items():
            resource_manager = json.loads(resource_manager_str)
            res[name] = resource_manager
        return res

    async def allocations(self, allocation_id=None):
        conn = await self.asyncconn
        if allocation_id:
            allocations = await conn.hget("allocations", allocation_id)
            return json.loads(allocations)
        else:
            res = dict()
            allocations = await conn.hgetall_asdict("allocations")
            for id, allocation_str in allocations.items():
                res[id] = json.loads(allocation_str)
            return res

    async def save_request(self, request):
        conn = await self.asyncconn
        allocation_id = str(uuid.uuid4())
        request['status'] = "received"
        request['allocation_id'] = allocation_id
        await conn.hset('allocations', allocation_id, json.dumps(request))
        return allocation_id

    async def update_status(self, allocation_id, **kwargs):
        conn = await self.asyncconn
        allocation = await self.allocations(allocation_id)
        allocation.update(kwargs)
        await conn.hset('allocations', allocation["allocation_id"], json.dumps(allocation))

    async def delete(self, key, fields):
        fields = fields if type(fields) is list else [fields]
        conn = await self.asyncconn
        await conn.hdel(key, fields)


REDIS = RedisClient(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", "6379"),
    username="",  # os.getenv("REDIS_USER"),
    password="",  # os.getenv("REDIS_PASSWORD"),
    db=os.getenv("REDIS_DB", 0),
)
