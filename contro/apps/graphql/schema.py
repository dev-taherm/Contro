import graphene

from contro.apps.graphql.dynamic import build_schema


class FallbackQuery(graphene.ObjectType):
    hello = graphene.String(description="Health check field.")

    def resolve_hello(self, info):
        return "Contro GraphQL API"


try:
    schema = build_schema()
except Exception:
    schema = graphene.Schema(query=FallbackQuery)
