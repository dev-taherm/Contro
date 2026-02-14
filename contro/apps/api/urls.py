from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from contro.apps.api.views import DynamicContentViewSet

content_list = DynamicContentViewSet.as_view({"get": "list", "post": "create"})
content_detail = DynamicContentViewSet.as_view(
    {"get": "retrieve", "put": "update", "patch": "partial_update", "delete": "destroy"}
)

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/token/verify/", TokenVerifyView.as_view(), name="token_verify"),
    path("content/<slug:content_type>/", content_list, name="dynamic_content_list"),
    path("content/<slug:content_type>/<int:pk>/", content_detail, name="dynamic_content_detail"),
]
