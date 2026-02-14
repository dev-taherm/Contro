from __future__ import annotations

from rest_framework.permissions import BasePermission, SAFE_METHODS

from contro.apps.iam.authentication import ApiTokenCredentials
from contro.apps.iam.services.tokens import token_has_permission


class DynamicContentPermission(BasePermission):
    def has_permission(self, request, view):
        model = getattr(view, "model", None)
        if model is None and hasattr(view, "get_model"):
            model = view.get_model()
        if model is None:
            return False

        perm = _perm_from_method(request.method, model)
        if not perm:
            return False

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not user.has_perm(perm):
            return False

        return _token_allows(request, perm)

    def has_object_permission(self, request, view, obj):
        model = obj.__class__
        perm = _perm_from_method(request.method, model)
        if not perm:
            return False

        user = request.user
        if not user or not user.is_authenticated:
            return False

        if not user.has_perm(perm, obj=obj):
            return False

        return _token_allows(request, perm)


def _perm_from_method(method: str, model) -> str | None:
    if method in SAFE_METHODS:
        action = "view"
    elif method == "POST":
        action = "add"
    elif method in {"PUT", "PATCH"}:
        action = "change"
    elif method == "DELETE":
        action = "delete"
    else:
        return None

    return f"content.{action}_{model._meta.model_name}"


def _token_allows(request, perm: str) -> bool:
    if isinstance(request.auth, ApiTokenCredentials):
        return token_has_permission(request.auth.token, perm)
    return True
