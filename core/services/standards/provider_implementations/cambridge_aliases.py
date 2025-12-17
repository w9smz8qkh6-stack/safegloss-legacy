"""
Alias providers for Cambridge programs.

All delegate to CambridgeProvider but register under specific program codes used in seeds.
"""
from core.services.standards.provider_implementations.cambridge import CambridgeProvider
from core.services.standards.providers import register_provider


@register_provider("CAM_PRIMARY")
class CambridgePrimaryProvider(CambridgeProvider):
    @property
    def program_code(self) -> str:
        return "CAM_PRIMARY"


@register_provider("CAM_LOWER_SECONDARY")
class CambridgeLowerSecondaryProvider(CambridgeProvider):
    @property
    def program_code(self) -> str:
        return "CAM_LOWER_SECONDARY"


@register_provider("CAM_IGCSE")
class CambridgeIGCSEProvider(CambridgeProvider):
    @property
    def program_code(self) -> str:
        return "CAM_IGCSE"


@register_provider("CAM_O_LEVEL")
class CambridgeOLevelProvider(CambridgeProvider):
    @property
    def program_code(self) -> str:
        return "CAM_O_LEVEL"


@register_provider("CAM_AS_A_LEVEL")
class CambridgeASLevelProvider(CambridgeProvider):
    @property
    def program_code(self) -> str:
        return "CAM_AS_A_LEVEL"
