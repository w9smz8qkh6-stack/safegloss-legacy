"""
Resource Discovery Service.

Provides functionality for discovering educational resources
(textbooks, courses, videos) that support learning objectives
from various standards authorities.

Each authority has its own provider that knows where to search
for official and recommended resources.
"""

from .base import (
    BaseResourceProvider,
    ResourceData,
    DiscoveryResult,
    ResourceProviderError,
    register_resource_provider,
    get_resource_provider,
    list_registered_resource_providers,
    create_resource_provider,
)

__all__ = [
    "BaseResourceProvider",
    "ResourceData",
    "DiscoveryResult",
    "ResourceProviderError",
    "register_resource_provider",
    "get_resource_provider",
    "list_registered_resource_providers",
    "create_resource_provider",
]

# Import provider implementations to trigger registration
from . import providers as _providers_module  # noqa: F401
