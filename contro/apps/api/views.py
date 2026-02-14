from __future__ import annotations

from django.shortcuts import get_object_or_404
from rest_framework import viewsets

from contro.apps.api.permissions import DynamicContentPermission
from contro.apps.content.models import ContentTypeDefinition
from contro.apps.content.services.schema import get_dynamic_model
from contro.apps.content.services.serializers import get_serializer_for_model
from contro.apps.content.services.hooks import run_hooks


class DynamicContentViewSet(viewsets.ModelViewSet):
    permission_classes = [DynamicContentPermission]

    def _get_content_type(self) -> ContentTypeDefinition:
        return get_object_or_404(ContentTypeDefinition, slug=self.kwargs["content_type"], is_active=True)

    def get_model(self):
        if hasattr(self, "_model") and self._model is not None:
            return self._model
        content_type = self._get_content_type()
        model = get_dynamic_model(content_type)
        self.model = model
        self._model = model
        return model

    def get_queryset(self):
        model = self.get_model()
        return model.objects.all()

    def get_serializer_class(self):
        model = self.get_model()
        return get_serializer_for_model(model)

    def perform_create(self, serializer):
        run_hooks("pre_create", data=serializer.validated_data, request=self.request)
        instance = serializer.save()
        run_hooks("post_create", instance=instance, request=self.request)

    def perform_update(self, serializer):
        instance = self.get_object()
        run_hooks("pre_update", instance=instance, data=serializer.validated_data, request=self.request)
        instance = serializer.save()
        run_hooks("post_update", instance=instance, request=self.request)

    def perform_destroy(self, instance):
        run_hooks("pre_delete", instance=instance, request=self.request)
        instance.delete()
        run_hooks("post_delete", instance=instance, request=self.request)
