from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0019_add_recommendation_tier_fields"),
    ]

    operations = [
        migrations.CreateModel(
            name="Text",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=500)),
                ("subtitle", models.CharField(blank=True, max_length=500)),
                ("authors", models.JSONField(blank=True, default=list)),
                ("publisher", models.CharField(blank=True, max_length=255)),
                ("edition", models.CharField(blank=True, max_length=100)),
                ("publication_year", models.IntegerField(blank=True, null=True)),
                ("isbn10", models.CharField(blank=True, db_index=True, max_length=20)),
                ("isbn13", models.CharField(blank=True, db_index=True, max_length=20)),
                ("oclc", models.CharField(blank=True, db_index=True, max_length=50)),
                ("lccn", models.CharField(blank=True, db_index=True, max_length=50)),
                ("language_code", models.CharField(blank=True, max_length=10)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="TextSource",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255, unique=True)),
                ("source_type", models.CharField(choices=[("library", "Library"), ("publisher", "Publisher"), ("oer", "OER"), ("index", "Index"), ("marketplace", "Marketplace")], max_length=20)),
                ("auth_method", models.CharField(choices=[("none", "None"), ("oauth", "OAuth"), ("saml", "SAML/SSO"), ("card_pin", "LibraryCard+PIN"), ("proxy_vpn", "Proxy/VPN"), ("api_key", "API Key")], default="none", max_length=20)),
                ("supports_api", models.BooleanField(default=False)),
                ("discovery_methods", models.JSONField(blank=True, default=list)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="CourseText",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("requirement_level", models.CharField(choices=[("required", "Required"), ("recommended", "Recommended"), ("alternative", "Alternative")], default="required", max_length=20)),
                ("notes", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_texts", to="core.course")),
                ("text", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="course_links", to="acquire.text")),
            ],
            options={
                "unique_together": {("course", "text", "requirement_level")},
                "indexes": [models.Index(fields=["course", "requirement_level"], name="acquire_cou_course__e77f4c_idx")],
            },
        ),
        migrations.CreateModel(
            name="UserTextSourceCredential",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("auth_method", models.CharField(choices=[("none", "None"), ("oauth", "OAuth"), ("saml", "SAML/SSO"), ("card_pin", "LibraryCard+PIN"), ("proxy_vpn", "Proxy/VPN"), ("api_key", "API Key")], default="none", max_length=20)),
                ("encrypted_secret_blob", models.TextField(help_text="Encrypted secret or token reference")),
                ("scopes", models.JSONField(blank=True, default=list, help_text="Connector-declared capabilities")),
                ("last_validated_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("text_source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="credentials", to="acquire.textsource")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="text_source_credentials", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "unique_together": {("user", "text_source")},
            },
        ),
        migrations.CreateModel(
            name="AcquisitionCandidate",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("match_score", models.FloatField(default=0)),
                ("match_signals", models.JSONField(blank=True, default=dict)),
                ("access_type", models.CharField(choices=[("borrow", "Borrow"), ("read_online", "Read Online"), ("download_open", "Download Open"), ("purchase_only", "Purchase Only"), ("login_required", "Login Required")], max_length=20)),
                ("url", models.TextField()),
                ("availability_snapshot", models.JSONField(blank=True, default=dict)),
                ("price_amount", models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
                ("price_currency", models.CharField(blank=True, max_length=10)),
                ("fetched_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("expires_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("text", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acquisition_candidates", to="acquire.text")),
                ("text_source", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="candidates", to="acquire.textsource")),
            ],
            options={
                "indexes": [models.Index(fields=["text", "text_source"], name="acquire_acq_text_id_f83caf_idx"), models.Index(fields=["access_type"], name="acquire_acq_access__4f32ff_idx")],
            },
        ),
        migrations.CreateModel(
            name="AcquisitionLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("actor_role", models.CharField(choices=[("admin", "Admin"), ("teacher_dev_override", "Teacher Dev Override")], max_length=30)),
                ("method", models.CharField(choices=[("api", "API"), ("oauth", "OAuth"), ("card_pin", "Card+PIN"), ("automation", "Automation"), ("manual", "Manual")], max_length=20)),
                ("action", models.CharField(choices=[("search", "Search"), ("availability", "Availability"), ("hold", "Hold"), ("borrow", "Borrow"), ("save_link", "Save Link"), ("open", "Open")], max_length=20)),
                ("result", models.CharField(choices=[("success", "Success"), ("blocked", "Blocked"), ("error", "Error")], max_length=20)),
                ("error_code", models.CharField(blank=True, max_length=100)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now)),
                ("course", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acquisition_logs", to="core.course")),
                ("text", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acquisition_logs", to="acquire.text")),
                ("text_source", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="acquisition_logs", to="acquire.textsource")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="acquisition_logs", to=settings.AUTH_USER_MODEL)),
            ],
            options={
                "indexes": [models.Index(fields=["course", "text", "action"], name="acquire_acq_course_i_390418_idx"), models.Index(fields=["text_source"], name="acquire_acq_text_so_9910c1_idx"), models.Index(fields=["created_at"], name="acquire_acq_created_9a4ba1_idx")],
            },
        ),
        migrations.AddIndex(
            model_name="text",
            index=models.Index(fields=["isbn13"], name="acquire_text_isbn13_71fab2_idx"),
        ),
        migrations.AddIndex(
            model_name="text",
            index=models.Index(fields=["isbn10"], name="acquire_text_isbn10_e2d9ce_idx"),
        ),
        migrations.AddIndex(
            model_name="text",
            index=models.Index(fields=["oclc"], name="acquire_text_oclc_da992f_idx"),
        ),
    ]
