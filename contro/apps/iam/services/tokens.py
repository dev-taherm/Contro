from __future__ import annotations

from typing import Iterable

from django.contrib.auth.models import Permission
from django.utils import timezone

from contro.apps.iam.models import ApiToken, User


def create_api_token(
    *,
    user: User,
    name: str,
    permissions: Iterable[Permission] | None = None,
    expires_at=None,
) -> tuple[ApiToken, str]:
    raw_token = ApiToken.generate_raw_token()
    token_prefix = raw_token.split(".", 1)[0]
    token_hash = ApiToken.hash_token(raw_token)

    api_token = ApiToken.objects.create(
        user=user,
        name=name,
        token_prefix=token_prefix,
        token_hash=token_hash,
        expires_at=expires_at,
    )

    if permissions:
        api_token.permissions.add(*permissions)

    return api_token, raw_token


def revoke_api_token(api_token: ApiToken) -> None:
    api_token.is_active = False
    api_token.save(update_fields=["is_active"])


def is_token_valid(api_token: ApiToken) -> bool:
    if not api_token.is_active:
        return False
    if api_token.expires_at and timezone.now() >= api_token.expires_at:
        return False
    return True


def token_has_permission(api_token: ApiToken, perm: str) -> bool:
    if not api_token.permissions.exists():
        return True

    if "." not in perm:
        return False
    app_label, codename = perm.split(".", 1)
    return api_token.permissions.filter(
        content_type__app_label=app_label,
        codename=codename,
    ).exists()
