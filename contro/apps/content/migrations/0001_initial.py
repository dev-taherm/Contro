from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ContentTypeDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=160, unique=True)),
                ("plural_name", models.CharField(blank=True, max_length=170)),
                ("description", models.TextField(blank=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Content Type",
                "verbose_name_plural": "Content Types",
                "ordering": ["name"],
            },
        ),
        migrations.CreateModel(
            name="ContentFieldDefinition",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=150)),
                ("slug", models.SlugField(max_length=160)),
                (
                    "field_type",
                    models.CharField(
                        choices=[
                            ("text", "Text"),
                            ("number", "Number"),
                            ("boolean", "Boolean"),
                            ("date", "Date"),
                            ("slug", "Slug"),
                            ("media", "Media (Single)"),
                            ("media_m2m", "Media (Multiple)"),
                            ("fk", "Foreign Key"),
                            ("m2m", "Many to Many"),
                        ],
                        max_length=20,
                    ),
                ),
                ("required", models.BooleanField(default=False)),
                ("unique", models.BooleanField(default=False)),
                ("default_value", models.JSONField(blank=True, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("related_name", models.CharField(blank=True, max_length=150)),
                ("order", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(default=django.utils.timezone.now, editable=False)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "content_type",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="fields",
                        to="content.contenttypedefinition",
                    ),
                ),
                (
                    "relation_target",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="related_fields",
                        to="content.contenttypedefinition",
                    ),
                ),
            ],
            options={
                "verbose_name": "Content Field",
                "verbose_name_plural": "Content Fields",
                "ordering": ["order", "name"],
            },
        ),
        migrations.AddConstraint(
            model_name="contentfielddefinition",
            constraint=models.UniqueConstraint(
                fields=("content_type", "slug"),
                name="unique_field_slug_per_content_type",
            ),
        ),
    ]
