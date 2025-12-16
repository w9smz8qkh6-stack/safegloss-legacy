from django.core.management.base import BaseCommand

from acquire.models import TextSource


DEFAULT_SOURCES = [
    {
        "name": "Google Books",
        "source_type": TextSource.INDEX,
        "auth_method": TextSource.AUTH_NONE,
        "supports_api": True,
        "discovery_methods": ["api"],
    },
    {
        "name": "Open Library",
        "source_type": TextSource.OER,
        "auth_method": TextSource.AUTH_NONE,
        "supports_api": True,
        "discovery_methods": ["api"],
    },
    {
        "name": "UVA Libraries",
        "source_type": TextSource.LIBRARY,
        "auth_method": TextSource.AUTH_SAML,
        "supports_api": True,
        "discovery_methods": ["api", "resolver_link"],
    },
    {
        "name": "NYPL",
        "source_type": TextSource.LIBRARY,
        "auth_method": TextSource.AUTH_CARD_PIN,
        "supports_api": False,
        "discovery_methods": ["catalog_link"],
    },
    {
        "name": "Marketplace Purchase",
        "source_type": TextSource.MARKETPLACE,
        "auth_method": TextSource.AUTH_NONE,
        "supports_api": False,
        "discovery_methods": ["scrape"],
    },
]


class Command(BaseCommand):
    help = "Seed default TextSource entries for acquisition connectors."

    def handle(self, *args, **options):
        created = 0
        for source in DEFAULT_SOURCES:
            obj, was_created = TextSource.objects.get_or_create(
                name=source["name"],
                defaults={
                    "source_type": source["source_type"],
                    "auth_method": source["auth_method"],
                    "supports_api": source["supports_api"],
                    "discovery_methods": source["discovery_methods"],
                },
            )
            created += int(was_created)
        self.stdout.write(self.style.SUCCESS(f"Seeded TextSource entries (created {created})"))
