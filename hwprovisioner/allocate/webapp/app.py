"""
The entrypoint of the allocate service

python -m webapp.app serve
"""
import os
import weakref
import random

import connexion

from .redisclient import REDIS
from .settings import log
from .expires import expire


random.seed(1)


def checkenv():
    """
    ensures the environment is configured correctly
    """
    missing = []
    r_fields = [
        "REDIS_PORT",
        "REDIS_HOST",
        "REDIS_DB",
        "REDIS_USER",
        "REDIS_PASSWORD",
    ]
    for field in r_fields:
        if not os.getenv(field):
            missing.append(field)
    if missing:
        raise EnvironmentError(
            "The following environment variables are not set: %s"
            % ", ".join(missing)
        )


def run_app(run=True, port=8080):
    """
    runs the web application
    """
    checkenv()
    log.debug("initiating application")
    cxapp = connexion.AioHttpApp(
        __name__, port=port, specification_dir="swagger/",
    )
    allocate = cxapp.add_api(
        "allocate.yml", base_path="/api", pass_context_arg_name="request",
    )
    allocate.subapp["websockets"] = weakref.WeakSet()
    allocate.subapp["redis"] = REDIS

    cxapp.app.on_startup.append(startup_daemons)
    cxapp.app.on_cleanup.append(cleanup_daemons)

    if run:
        return cxapp.run()
    return cxapp.app


async def startup_daemons(app):
    """
    background tasks
    """
    app["expired_jobs"] = app.loop.create_task(expire(REDIS))


async def cleanup_daemons(app):
    """
    task tidyups
    """
    app["expired_jobs"].cancel()


if __name__ == "__main__":
    run_app()
