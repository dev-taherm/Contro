from __future__ import annotations

import graphene
from graphene_django.types import DjangoObjectType
from graphql import GraphQLError

from django.db.utils import OperationalError

from contro.apps.content.models import ContentFieldDefinition, ContentTypeDefinition
from contro.apps.content.services.schema import get_dynamic_model
from contro.apps.iam.authentication import ApiTokenCredentials
from contro.apps.iam.services.tokens import token_has_permission


def build_schema() -> graphene.Schema:
    try:
        content_types = ContentTypeDefinition.objects.filter(is_active=True).prefetch_related("fields")
    except OperationalError:
        return graphene.Schema(query=_fallback_query())
    if not content_types.exists():
        return graphene.Schema(query=_fallback_query())

    type_map = {}
    for content_type in content_types:
        model = get_dynamic_model(content_type)
        type_map[content_type.slug] = _build_graphene_type(model)

    query_cls = _build_query(content_types, type_map)
    mutation_cls = _build_mutation(content_types, type_map)

    return graphene.Schema(query=query_cls, mutation=mutation_cls)


def _fallback_query():
    class Query(graphene.ObjectType):
        hello = graphene.String(description="Health check field.")

        def resolve_hello(self, info):
            return "Contro GraphQL API"

    return Query


def _build_graphene_type(model):
    class Meta:
        model = model
        fields = "__all__"

    return type(f"{model.__name__}Type", (DjangoObjectType,), {"Meta": Meta})


def _build_query(content_types, type_map):
    attrs = {}
    for content_type in content_types:
        model = get_dynamic_model(content_type)
        gql_type = type_map[content_type.slug]
        list_name = _to_snake(content_type.plural_name or f"{content_type.slug}s")
        detail_name = _to_snake(content_type.slug)

        attrs[list_name] = graphene.List(gql_type)
        attrs[detail_name] = graphene.Field(gql_type, id=graphene.ID(required=True))

        attrs[f"resolve_{list_name}"] = _make_list_resolver(model)
        attrs[f"resolve_{detail_name}"] = _make_detail_resolver(model)

    return type("Query", (graphene.ObjectType,), attrs)


def _build_mutation(content_types, type_map):
    attrs = {}
    for content_type in content_types:
        model = get_dynamic_model(content_type)
        gql_type = type_map[content_type.slug]
        base_name = _to_snake(content_type.slug)

        create_mutation = _build_create_mutation(model, gql_type, content_type.fields.all())
        update_mutation = _build_update_mutation(model, gql_type, content_type.fields.all())
        delete_mutation = _build_delete_mutation(model)

        attrs[f"create_{base_name}"] = create_mutation.Field()
        attrs[f"update_{base_name}"] = update_mutation.Field()
        attrs[f"delete_{base_name}"] = delete_mutation.Field()

    return type("Mutation", (graphene.ObjectType,), attrs)


def _build_create_mutation(model, gql_type, field_defs):
    arguments = _build_mutation_arguments(field_defs, include_id=False)
    _attach_base_arguments(arguments, model, force_optional=False)

    def mutate(root, info, **kwargs):
        _require_perm(info, f"content.add_{model._meta.model_name}")
        data, m2m_data = _split_relations(model, field_defs, kwargs)
        instance = model.objects.create(**data)
        _apply_m2m(instance, m2m_data)
        return mutation_class(ok=True, result=instance)

    attrs = {
        "ok": graphene.Boolean(),
        "result": graphene.Field(gql_type),
        "Arguments": arguments,
        "mutate": mutate,
    }
    mutation_class = type(f"Create{model.__name__}", (graphene.Mutation,), attrs)
    return mutation_class


def _build_update_mutation(model, gql_type, field_defs):
    arguments = _build_mutation_arguments(field_defs, include_id=True, force_optional=True)
    _attach_base_arguments(arguments, model, force_optional=True)

    def mutate(root, info, **kwargs):
        _require_perm(info, f"content.change_{model._meta.model_name}")
        instance = model.objects.get(pk=kwargs.pop("id"))
        _require_perm(info, f"content.change_{model._meta.model_name}", obj=instance)
        data, m2m_data = _split_relations(model, field_defs, kwargs)
        for key, value in data.items():
            setattr(instance, key, value)
        instance.save()
        _apply_m2m(instance, m2m_data)
        return mutation_class(ok=True, result=instance)

    attrs = {
        "ok": graphene.Boolean(),
        "result": graphene.Field(gql_type),
        "Arguments": arguments,
        "mutate": mutate,
    }
    mutation_class = type(f"Update{model.__name__}", (graphene.Mutation,), attrs)
    return mutation_class


def _build_delete_mutation(model):
    class Arguments:
        id = graphene.ID(required=True)

    def mutate(root, info, id):
        instance = model.objects.get(pk=id)
        _require_perm(info, f"content.delete_{model._meta.model_name}", obj=instance)
        instance.delete()
        return mutation_class(ok=True)

    attrs = {
        "ok": graphene.Boolean(),
        "Arguments": Arguments,
        "mutate": mutate,
    }
    mutation_class = type(f"Delete{model.__name__}", (graphene.Mutation,), attrs)
    return mutation_class


def _build_mutation_arguments(field_defs, include_id: bool, force_optional: bool = False):
    attrs = {}
    if include_id:
        attrs["id"] = graphene.ID(required=True)

    for field_def in field_defs:
        attrs[field_def.slug] = _graphene_field_for_def(field_def, force_optional=force_optional)

    return type("Arguments", (), attrs)


def _graphene_field_for_def(field_def: ContentFieldDefinition, force_optional: bool = False):
    required = field_def.required and not force_optional
    if field_def.field_type == ContentFieldDefinition.FIELD_TEXT:
        return graphene.String(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_SLUG:
        return graphene.String(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_NUMBER:
        return graphene.Float(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_BOOLEAN:
        return graphene.Boolean(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_DATE:
        return graphene.Date(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_FK:
        return graphene.ID(required=required)
    if field_def.field_type == ContentFieldDefinition.FIELD_M2M:
        return graphene.List(graphene.ID, required=required)
    return graphene.String()


def _attach_base_arguments(arguments, model, force_optional: bool):
    if hasattr(model, "status"):
        setattr(arguments, "status", graphene.String(required=False))
    if hasattr(model, "published_at"):
        setattr(arguments, "published_at", graphene.DateTime(required=False))


def _make_list_resolver(model):
    def resolver(root, info):
        _require_perm(info, f"content.view_{model._meta.model_name}")
        return model.objects.all()

    return resolver


def _make_detail_resolver(model):
    def resolver(root, info, id):
        instance = model.objects.get(pk=id)
        _require_perm(info, f"content.view_{model._meta.model_name}", obj=instance)
        return instance

    return resolver


def _require_perm(info, perm: str, obj=None):
    request = info.context
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        raise GraphQLError("Authentication required")
    if not user.has_perm(perm, obj=obj):
        raise GraphQLError("Permission denied")

    if isinstance(request.auth, ApiTokenCredentials) and not token_has_permission(request.auth.token, perm):
        raise GraphQLError("API token not authorized")


def _split_relations(model, field_defs, data):
    values = {}
    m2m_values = {}
    field_slugs = {field_def.slug for field_def in field_defs}
    for field_def in field_defs:
        if field_def.slug not in data:
            continue
        if field_def.field_type == ContentFieldDefinition.FIELD_M2M:
            m2m_values[field_def.slug] = data[field_def.slug]
        elif field_def.field_type == ContentFieldDefinition.FIELD_FK:
            values[f"{field_def.slug}_id"] = data[field_def.slug]
        else:
            values[field_def.slug] = data[field_def.slug]
    for key, value in data.items():
        if key not in field_slugs:
            values[key] = value
    return values, m2m_values


def _apply_m2m(instance, m2m_data):
    for field_name, values in m2m_data.items():
        if values is None:
            continue
        getattr(instance, field_name).set(values)


def _to_snake(value: str) -> str:
    return value.replace(" ", "_").replace("-", "_").lower()
