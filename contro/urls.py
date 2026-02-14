from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from contro.apps.graphql.views import DynamicGraphQLView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("contro.apps.api.urls")),
    path("iam/", include("contro.apps.iam.urls")),
    path("content/", include("contro.apps.content.urls")),
    path("graphql/", DynamicGraphQLView.as_view(graphiql=settings.DEBUG)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
