from django.db import migrations


def add_wida(apps, schema_editor):
    StandardsAuthority = apps.get_model("core", "StandardsAuthority")
    AuthorityProgram = apps.get_model("core", "AuthorityProgram")

    wida, _ = StandardsAuthority.objects.get_or_create(
        code="WIDA",
        defaults={
            "name": "WIDA",
            "description": "English Language Development (ELD) standards",
            "is_active": True,
        },
    )

    AuthorityProgram.objects.get_or_create(
        authority=wida,
        code="WIDA_ACCESS",
        defaults={
            "name": "ACCESS for ELLs",
            "description": "WIDA English Language Development standards",
            "provider_key": "",
            "is_active": True,
        },
    )


def remove_wida(apps, schema_editor):
    AuthorityProgram = apps.get_model("core", "AuthorityProgram")
    StandardsAuthority = apps.get_model("core", "StandardsAuthority")

    AuthorityProgram.objects.filter(code="WIDA_ACCESS").delete()
    StandardsAuthority.objects.filter(code="WIDA").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_add_recommendation_tier_fields"),
    ]

    operations = [
        migrations.RunPython(add_wida, reverse_code=remove_wida),
    ]
