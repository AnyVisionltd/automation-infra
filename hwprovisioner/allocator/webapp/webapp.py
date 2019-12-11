"""
foo
"""
import logging

import asyncio
from aiohttp import web
from aiohttp_swagger import setup_swagger

from webapp.routes import setup_routes


CONFIG = {
    "api_prefix": "/api/v1/",
    "host": "0.0.0.0",
    "port": "8080",
    "show_errors": True,
}


async def init(loop):
    """
    initialize application
    """
    app = web.Application(loop=loop)

    # add all of our routes
    setup_routes(app)

    # set up all of our middlewares
    # ...

    host, port = CONFIG["host"], CONFIG["port"]
    return app, host, port


def main(argv=None):
    """
    run the webserver
    """
    logging.basicConfig(level=logging.DEBUG)
    loop = asyncio.get_event_loop()
    app, host, port = loop.run_until_complete(init(loop))
    setup_swagger(app, swagger_url="{}doc".format(CONFIG["api_prefix"]))
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    main()
