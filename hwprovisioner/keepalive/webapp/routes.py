"""
a centralised file for all of the service routes
"""
from webapp.renew import RenewView


def setup_routes(app):
    """
    all of the keepalive routes are defined here
    """
    app.router.add_view("/api/v1/renew/{alias}/{lockhash}", RenewView)
