from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable

from django.apps import apps
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.core.validators import MaxLengthValidator, MaxValueValidator, MinLengthValidator, MinValueValidator, RegexValidator
from django.db import connection, models
from django.db.utils import OperationalError
from django.utils.dateparse import parse_date

from contro.apps.content.models import ContentFieldDefinition, ContentTypeDefinition, DynamicContentBase


_DYNAMIC_MODELS: Dict[str, type] = {}


@dataclass
class SchemaSyncResult:
    model: type
    created_table: bool
    added_columns: list[str]
    created_m2m_tables: list[str]


def model_name_from_slug(slug: str) -> str:
    parts = slug.replace("_", "-").split("-")
    return "".join(part.capitalize() for part in parts if part) or "DynamicContent"


def _field_kwargs(field_def: ContentFieldDefinition) -> dict:
    kwargs = {
        "null": not field_def.required,
        "blank": not field_def.required,
        "unique": field_def.unique,
    }
    if field_def.default_value is not None:
        kwargs["default"] = field_def.default_value
    if field_def.metadata.get("db_index") is True:
        kwargs["db_index"] = True
    return kwargs


def _build_field(field_def: ContentFieldDefinition):
    kwargs = _field_kwargs(field_def)
    validators = _build_validators(field_def)
    if validators:
        kwargs["validators"] = validators

    if field_def.field_type == ContentFieldDefinition.FIELD_TEXT:
        max_length = field_def.metadata.get("max_length")
        if max_length:
            return models.CharField(max_length=int(max_length), **kwargs)
        return models.TextField(**kwargs)

    if field_def.field_type == ContentFieldDefinition.FIELD_NUMBER:
        if field_def.metadata.get("integer"):
            return models.IntegerField(**kwargs)
        return models.FloatField(**kwargs)

    if field_def.field_type == ContentFieldDefinition.FIELD_BOOLEAN:
        if field_def.required:
            return models.BooleanField(default=kwargs.pop("default", False), **kwargs)
        return models.BooleanField(null=True, **kwargs)

    if field_def.field_type == ContentFieldDefinition.FIELD_DATE:
        return models.DateField(**kwargs)

    if field_def.field_type == ContentFieldDefinition.FIELD_SLUG:
        max_length = field_def.metadata.get("max_length", 160)
        allow_unicode = bool(field_def.metadata.get("allow_unicode", False))
        return models.SlugField(max_length=int(max_length), allow_unicode=allow_unicode, **kwargs)

    if field_def.field_type == ContentFieldDefinition.FIELD_FK:
        target = _relation_target_label(field_def)
        related_name = _resolve_related_name(field_def)
        return models.ForeignKey(
            target,
            on_delete=models.CASCADE,
            related_name=related_name,
            **kwargs,
        )

    if field_def.field_type == ContentFieldDefinition.FIELD_M2M:
        target = _relation_target_label(field_def)
        related_name = _resolve_related_name(field_def)
        return models.ManyToManyField(target, related_name=related_name, blank=not field_def.required)

    raise ValueError(f"Unsupported field type: {field_def.field_type}")


def _build_validators(field_def: ContentFieldDefinition):
    validators = []
    metadata = field_def.metadata or {}

    if field_def.field_type in {ContentFieldDefinition.FIELD_TEXT, ContentFieldDefinition.FIELD_SLUG}:
        min_length = metadata.get("min_length")
        max_length = metadata.get("max_length")
        if min_length is not None:
            validators.append(MinLengthValidator(int(min_length)))
        if max_length is not None:
            validators.append(MaxLengthValidator(int(max_length)))
        regex = metadata.get("regex")
        if regex:
            validators.append(RegexValidator(regex))

    if field_def.field_type == ContentFieldDefinition.FIELD_NUMBER:
        min_value = metadata.get("min_value")
        max_value = metadata.get("max_value")
        if min_value is not None:
            validators.append(MinValueValidator(float(min_value)))
        if max_value is not None:
            validators.append(MaxValueValidator(float(max_value)))

    if field_def.field_type == ContentFieldDefinition.FIELD_DATE:
        min_date = metadata.get("min_date")
        max_date = metadata.get("max_date")
        if min_date:
            parsed = parse_date(str(min_date))
            if parsed:
                validators.append(MinValueValidator(parsed))
        if max_date:
            parsed = parse_date(str(max_date))
            if parsed:
                validators.append(MaxValueValidator(parsed))

    return validators


def _relation_target_label(field_def: ContentFieldDefinition) -> str:
    if not field_def.relation_target:
        raise ValueError("Relation target is required for relation fields")
    model_name = model_name_from_slug(field_def.relation_target.slug)
    return f"content.{model_name}"


def _resolve_related_name(field_def: ContentFieldDefinition) -> str:
    if field_def.related_name:
        return field_def.related_name
    return f"{field_def.content_type.slug}_{field_def.slug}_set"


def build_dynamic_model(content_type: ContentTypeDefinition) -> type:
    model_name = model_name_from_slug(content_type.slug)
    attrs: dict = {
        "__module__": "contro.apps.content.dynamic_models",
        "__str__": lambda self: f"{content_type.name} #{self.pk}",
        "__content_type_id__": content_type.id,
        "__content_type_slug__": content_type.slug,
    }

    for field_def in content_type.fields.order_by("order", "id"):
        attrs[field_def.slug] = _build_field(field_def)

    class Meta:
        app_label = "content"
        db_table = content_type.db_table
        verbose_name = content_type.name
        verbose_name_plural = content_type.plural_name or f"{content_type.name}s"

    attrs["Meta"] = Meta

    model_class = type(model_name, (DynamicContentBase,), attrs)
    return model_class


def register_dynamic_model(model_class: type) -> None:
    app_label = model_class._meta.app_label
    model_key = model_class._meta.model_name

    if model_key in apps.all_models[app_label]:
        apps.all_models[app_label][model_key] = model_class
    else:
        apps.register_model(app_label, model_class)

    apps.clear_cache()


def sync_schema(content_type: ContentTypeDefinition, _visited: set[str] | None = None) -> SchemaSyncResult:
    if _visited is None:
        _visited = set()
    if content_type.slug in _visited:
        model_class = build_dynamic_model(content_type)
        register_dynamic_model(model_class)
        return SchemaSyncResult(model=model_class, created_table=False, added_columns=[], created_m2m_tables=[])
    _visited.add(content_type.slug)

    relation_targets = content_type.fields.filter(
        field_type__in=[ContentFieldDefinition.FIELD_FK, ContentFieldDefinition.FIELD_M2M]
    ).select_related(\"relation_target\")
    for field_def in relation_targets:
        if field_def.relation_target and field_def.relation_target.slug != content_type.slug:
            sync_schema(field_def.relation_target, _visited=_visited)

    model_class = build_dynamic_model(content_type)
    register_dynamic_model(model_class)

    created_table = False
    added_columns: list[str] = []
    created_m2m_tables: list[str] = []

    with connection.cursor() as cursor:
        existing_tables = {table.name for table in connection.introspection.get_table_list(cursor)}

    if model_class._meta.db_table not in existing_tables:
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(model_class)
        created_table = True
    else:
        with connection.cursor() as cursor:
            existing_columns = {
                col.name for col in connection.introspection.get_table_description(cursor, model_class._meta.db_table)
            }
        with connection.schema_editor() as schema_editor:
            for field in model_class._meta.local_fields:
                if field.column not in existing_columns:
                    if not field.null and field.default is models.NOT_PROVIDED:
                        raise ValueError(
                            f"Cannot add required field '{field.name}' without a default. "
                            "Provide a default or make the field optional."
                        )
                    schema_editor.add_field(model_class, field)
                    added_columns.append(field.column)

    with connection.cursor() as cursor:
        existing_tables = {table.name for table in connection.introspection.get_table_list(cursor)}

    with connection.schema_editor() as schema_editor:
        for m2m_field in model_class._meta.local_many_to_many:
            through_table = m2m_field.remote_field.through._meta.db_table
            if through_table not in existing_tables:
                schema_editor.create_model(m2m_field.remote_field.through)
                created_m2m_tables.append(through_table)

    ensure_model_permissions(model_class)

    _DYNAMIC_MODELS[content_type.slug] = model_class

    return SchemaSyncResult(
        model=model_class,
        created_table=created_table,
        added_columns=added_columns,
        created_m2m_tables=created_m2m_tables,
    )


def ensure_model_permissions(model_class: type) -> None:
    content_type = ContentType.objects.get_for_model(model_class, for_concrete_model=False)
    for action in ("add", "change", "delete", "view"):
        codename = f"{action}_{model_class._meta.model_name}"
        name = f"Can {action} {model_class._meta.verbose_name}"
        Permission.objects.get_or_create(
            codename=codename,
            content_type=content_type,
            defaults={"name": name},
        )


def get_dynamic_model(content_type: ContentTypeDefinition) -> type:
    if content_type.slug in _DYNAMIC_MODELS:
        return _DYNAMIC_MODELS[content_type.slug]
    return sync_schema(content_type).model


def get_dynamic_model_by_slug(slug: str) -> type:
    if slug in _DYNAMIC_MODELS:
        return _DYNAMIC_MODELS[slug]
    content_type = ContentTypeDefinition.objects.get(slug=slug)
    return sync_schema(content_type).model


def load_all_models() -> Iterable[type]:
    models_list = []
    for content_type in ContentTypeDefinition.objects.filter(is_active=True):
        try:
            models_list.append(get_dynamic_model(content_type))
        except OperationalError:
            continue
    return models_list
