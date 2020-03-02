"""
redis singleton
"""
import redis
import asyncio_redis

import os


# pylint: disable=R0903
class RedisClient:
    """
    exposes a redis connection
    """

    # pylint: disable=too-many-arguments
    def __init__(self, host, port, username, password, db=None):
        self._conn = None
        self.host = host
        self.port = int(port)
        self.db = int(db)
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

    def __create_connection(self):
        self._conn = redis.Redis(connection_pool=self.pool)


REDIS = RedisClient(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=os.getenv("REDIS_PORT", "6379"),
    username="",  # os.getenv("REDIS_USER"),
    password="",  # os.getenv("REDIS_PASSWORD"),
    db=os.getenv("REDIS_DB"),
)
