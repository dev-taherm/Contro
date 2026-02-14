from __future__ import annotations

from dataclasses import dataclass

from django.utils import timezone
from rest_framework import authentication, exceptions
from rest_framework.authentication import get_authorization_header

from contro.apps.iam.models import ApiToken


@dataclass
class ApiTokenCredentials:
    token: ApiToken
    raw_token: str


class ApiTokenAuthentication(authentication.BaseAuthentication):
    keyword = "Token"

    def authenticate(self, request):
        raw_token = self._get_token_from_headers(request)
        if not raw_token:
            return None

        token_hash = ApiToken.hash_token(raw_token)
        try:
            api_token = (
                ApiToken.objects.select_related("user")
                .prefetch_related("permissions")
                .get(token_hash=token_hash)
            )
        except ApiToken.DoesNotExist:
            raise exceptions.AuthenticationFailed("Invalid API token.")

        if not api_token.is_active or api_token.is_expired():
            raise exceptions.AuthenticationFailed("API token is inactive or expired.")

        api_token.last_used_at = timezone.now()
        api_token.save(update_fields=["last_used_at"])

        return (api_token.user, ApiTokenCredentials(token=api_token, raw_token=raw_token))

    def authenticate_header(self, request):
        return self.keyword

    def _get_token_from_headers(self, request) -> str | None:
        auth = get_authorization_header(request).decode("utf-8")
        if auth:
            parts = auth.split()
            if len(parts) == 2 and parts[0].lower() == self.keyword.lower():
                return parts[1]

        token = request.headers.get("X-API-Token")
        if token:
            return token.strip()

        return None
