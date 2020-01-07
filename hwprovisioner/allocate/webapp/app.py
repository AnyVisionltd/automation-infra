"""
The entrypoint of the allocate service

python -m webapp.app serve
"""
import weakref

import connexion

from .settings import log


def run_app(run=True, port=8080):
    """
    runs the web application
    """
    log.debug("initiating application")
    cxapp = connexion.AioHttpApp(
        __name__, port=port, specification_dir="swagger/",
    )
    cxapp.app["websockets"] = weakref.WeakSet()
    cxapp.add_api(
        "allocate.yml", base_path="/api", pass_context_arg_name="request",
    )

    if run:
        return cxapp.run()
    return cxapp.app


if __name__ == "__main__":
    run_app()
