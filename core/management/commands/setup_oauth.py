"""
Management command to set up Google OAuth for django-allauth.

Reads credentials from environment variables:
- GOOGLE_CLIENT_ID
- GOOGLE_CLIENT_SECRET
- SITE_DOMAIN (optional, to update Django Site domain)

Usage:
    python manage.py setup_oauth
"""

import os

from django.core.management.base import BaseCommand
from django.contrib.sites.models import Site

from allauth.socialaccount.models import SocialApp


class Command(BaseCommand):
    help = "Set up Google OAuth SocialApp from environment variables"

    def handle(self, *args, **options):
        # Update Site domain if SITE_DOMAIN is set
        site_domain = os.environ.get("SITE_DOMAIN")
        if site_domain:
            site = Site.objects.get(pk=1)
            old_domain = site.domain
            site.domain = site_domain
            site.name = site_domain
            site.save()
            self.stdout.write(
                self.style.SUCCESS(f"Updated Site domain: {old_domain} -> {site_domain}")
            )

        client_id = os.environ.get("GOOGLE_CLIENT_ID")
        client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")

        if not client_id or not client_secret:
            self.stdout.write(
                self.style.WARNING(
                    "GOOGLE_CLIENT_ID and/or GOOGLE_CLIENT_SECRET not set. "
                    "Skipping OAuth setup."
                )
            )
            return

        # Get or create the Google SocialApp
        social_app, created = SocialApp.objects.update_or_create(
            provider="google",
            defaults={
                "name": "Google",
                "client_id": client_id,
                "secret": client_secret,
            },
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS("Created Google SocialApp")
            )
        else:
            self.stdout.write(
                self.style.SUCCESS("Updated Google SocialApp")
            )

        # Associate with all sites
        sites = Site.objects.all()
        for site in sites:
            social_app.sites.add(site)
            self.stdout.write(f"  - Associated with site: {site.domain}")

        self.stdout.write(
            self.style.SUCCESS("Google OAuth setup complete!")
        )
