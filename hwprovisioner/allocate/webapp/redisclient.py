"""
redis singleton
"""
import os

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


REDIS = RedisClient(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", "6379"),
    username="",  # os.getenv("REDIS_USER"),
    password="",  # os.getenv("REDIS_PASSWORD"),
    db=os.getenv("REDIS_DB", 0),
)
