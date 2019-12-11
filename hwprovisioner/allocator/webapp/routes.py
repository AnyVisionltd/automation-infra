"""
a centralised file for all of the service routes
"""
from webapp.lock import LockView
from webapp.inventory import InventoryView


def setup_routes(app):
    """
    all of the allocator routes are defined here
    """
    app.router.add_view("/api/v1/lock/", LockView)
    app.router.add_view("/api/v1/inventory/", InventoryView)
