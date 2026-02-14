from django.contrib.auth.models import AnonymousUser
from graphene_django.views import GraphQLView
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

from contro.apps.graphql.dynamic import build_schema
from contro.apps.iam.authentication import ApiTokenAuthentication


class DynamicGraphQLView(GraphQLView):
    authentication_classes = (ApiTokenAuthentication, JWTAuthentication)

    def get_schema(self, request=None):
        return build_schema()

    def get_context(self, request):
        if not getattr(request, "user", None) or not request.user.is_authenticated:
            for auth_class in self.authentication_classes:
                try:
                    result = auth_class().authenticate(request)
                except AuthenticationFailed:
                    result = None
                if result:
                    request.user, request.auth = result
                    break
        if not getattr(request, "user", None):
            request.user = AnonymousUser()
        return request
