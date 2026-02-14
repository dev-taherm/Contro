from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class DynamicContentBase(models.Model):
    STATUS_DRAFT = "draft"
    STATUS_PUBLISHED = "published"

    STATUS_CHOICES = (
        (STATUS_DRAFT, "Draft"),
        (STATUS_PUBLISHED, "Published"),
    )

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True

    def publish(self):
        self.status = self.STATUS_PUBLISHED
        if not self.published_at:
            self.published_at = timezone.now()

    def unpublish(self):
        self.status = self.STATUS_DRAFT
        self.published_at = None

    @property
    def is_published(self) -> bool:
        return self.status == self.STATUS_PUBLISHED

    def save(self, *args, **kwargs):
        self._apply_slug_sources()
        return super().save(*args, **kwargs)

    def _apply_slug_sources(self):
        content_type_id = getattr(self, "__content_type_id__", None)
        if not content_type_id:
            return
        from django.apps import apps

        ContentFieldDefinition = apps.get_model("content", "ContentFieldDefinition")
        field_defs = ContentFieldDefinition.objects.filter(
            content_type_id=content_type_id, field_type=ContentFieldDefinition.FIELD_SLUG
        )
        for field_def in field_defs:
            if getattr(self, field_def.slug):
                continue
            source = field_def.metadata.get("source")
            if not source:
                continue
            source_value = getattr(self, source, None)
            if source_value:
                allow_unicode = bool(field_def.metadata.get("allow_unicode", False))
                setattr(self, field_def.slug, slugify(str(source_value), allow_unicode=allow_unicode))


class ContentTypeDefinition(models.Model):
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160, unique=True)
    plural_name = models.CharField(max_length=170, blank=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content Type"
        verbose_name_plural = "Content Types"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def clean(self):
        if not self.slug:
            self.slug = slugify(self.name)
        if not self.plural_name:
            self.plural_name = f"{self.name}s"
        if self.pk:
            original = ContentTypeDefinition.objects.filter(pk=self.pk).values("slug").first()
            if original and original["slug"] != self.slug:
                raise ValidationError("Slug cannot be changed once created.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    @property
    def db_table(self) -> str:
        return f"content_{self.slug.replace('-', '_')}"


class ContentFieldDefinition(models.Model):
    FIELD_TEXT = "text"
    FIELD_NUMBER = "number"
    FIELD_BOOLEAN = "boolean"
    FIELD_DATE = "date"
    FIELD_SLUG = "slug"
    FIELD_FK = "fk"
    FIELD_M2M = "m2m"

    FIELD_TYPES = (
        (FIELD_TEXT, "Text"),
        (FIELD_NUMBER, "Number"),
        (FIELD_BOOLEAN, "Boolean"),
        (FIELD_DATE, "Date"),
        (FIELD_SLUG, "Slug"),
        (FIELD_FK, "Foreign Key"),
        (FIELD_M2M, "Many to Many"),
    )

    content_type = models.ForeignKey(
        ContentTypeDefinition,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    name = models.CharField(max_length=150)
    slug = models.SlugField(max_length=160)
    field_type = models.CharField(max_length=20, choices=FIELD_TYPES)

    required = models.BooleanField(default=False)
    unique = models.BooleanField(default=False)
    default_value = models.JSONField(null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    relation_target = models.ForeignKey(
        ContentTypeDefinition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_fields",
    )
    related_name = models.CharField(max_length=150, blank=True)

    order = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(default=timezone.now, editable=False)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Content Field"
        verbose_name_plural = "Content Fields"
        ordering = ["order", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["content_type", "slug"],
                name="unique_field_slug_per_content_type",
            )
        ]

    def __str__(self) -> str:
        return f"{self.content_type.name}: {self.name}"

    def clean(self):
        if not self.slug:
            self.slug = slugify(self.name).replace("-", "_")
        else:
            self.slug = self.slug.replace("-", "_")
        if not self.slug.isidentifier():
            raise ValidationError("Field slug must be a valid Python identifier.")
        if self.slug in {"id", "created_at", "updated_at", "status", "published_at"}:
            raise ValidationError("Field slug conflicts with reserved system fields.")
        if self.pk:
            original = ContentFieldDefinition.objects.filter(pk=self.pk).values("slug").first()
            if original and original["slug"] != self.slug:
                raise ValidationError("Field slug cannot be changed once created.")
        if self.field_type in {self.FIELD_FK, self.FIELD_M2M} and not self.relation_target:
            raise ValidationError("Relation target is required for FK and M2M fields.")
        if self.field_type not in {self.FIELD_FK, self.FIELD_M2M} and self.relation_target:
            raise ValidationError("Relation target can only be set for FK and M2M fields.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
