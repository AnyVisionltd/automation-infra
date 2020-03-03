"""
The entrypoint of the resource manager service

python -m webapp.app serve
"""
import weakref

import asyncio
import connexion

from .listener import LISTENER
from .processor import PROCESSOR
from .config import CONFIG
from .settings import log


def run_app(run=True, port=9080):
    """
    runs the web application
    """
    log.debug("initiating application")
    cxapp = connexion.AioHttpApp(
        __name__, port=port, specification_dir="swagger/",
    )
    cxapp.app["websockets"] = weakref.WeakSet()
    cxapp.add_api(  # nosec
        "resourcemgr.yml", base_path="/api", pass_context_arg_name="request",
    )
    cxapp.app.on_startup.append(start_daemons)
    cxapp.app.on_cleanup.append(cleanup_daemons)

    if run:
        return cxapp.run()
    return cxapp.app


async def start_daemons(app):
    """
    background tasks
    """
    # a single listener runs to volunteer
    app["listen"] = app.loop.create_task(LISTENER.listen(app))

    # we want a dedicated processor for each inventory item
    app["process"] = []
    for rtype in CONFIG["resources"]:
        for rref in CONFIG["resources"][rtype]:
            app["process"].append(
                app.loop.create_task(PROCESSOR.process(rtype, rref))
            )


async def cleanup_daemons(app):
    """
    application tidy ups
    """
    for proc in app["process"]:
        proc.cancel()
    app["listen"].cancel()


if __name__ == "__main__":
    run_app()
