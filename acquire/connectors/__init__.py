"""
Connector registry for text acquisition providers.

Each connector should expose a `search` method and declare its capabilities.
This module provides a simple registry for lookup and instantiation of the
default connector set.
"""

CONNECTOR_REGISTRY = {}


def register_connector(name: str, connector) -> None:
    """Register a connector instance under a stable name."""
    CONNECTOR_REGISTRY[name] = connector


def get_connector(name: str):
    """Return a connector instance by name, or None if unregistered."""
    return CONNECTOR_REGISTRY.get(name)


def initialize_default_connectors() -> None:
    """
    Register built-in connector implementations.

    This keeps import-time side effects contained to a single call.
    """
    from .google_books import GoogleBooksConnector
    from .open_library import OpenLibraryConnector
    from .uva_primo import UVAConnector
    from .nypl_catalog import NYPLConnector
    from .marketplace_purchase import MarketplacePurchaseConnector

    register_connector("google_books", GoogleBooksConnector())
    register_connector("open_library", OpenLibraryConnector())
    register_connector("uva_primo", UVAConnector())
    register_connector("nypl_catalog", NYPLConnector())
    register_connector("marketplace_purchase", MarketplacePurchaseConnector())
