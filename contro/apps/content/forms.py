from __future__ import annotations

from django import forms
from django.forms import modelform_factory

from contro.apps.content.models import ContentFieldDefinition, ContentTypeDefinition
from contro.apps.content.services.schema import get_dynamic_model


class ContentTypeForm(forms.ModelForm):
    class Meta:
        model = ContentTypeDefinition
        fields = ["name", "slug", "plural_name", "description", "metadata", "is_active"]
        widgets = {
            "metadata": forms.Textarea(attrs={"rows": 3}),
        }


class ContentFieldForm(forms.ModelForm):
    class Meta:
        model = ContentFieldDefinition
        fields = [
            "name",
            "slug",
            "field_type",
            "required",
            "unique",
            "default_value",
            "metadata",
            "relation_target",
            "related_name",
            "order",
        ]
        widgets = {
            "metadata": forms.Textarea(attrs={"rows": 3}),
            "default_value": forms.Textarea(attrs={"rows": 2}),
        }


def content_entry_form(content_type: ContentTypeDefinition):
    model = get_dynamic_model(content_type)
    excluded = {"created_at", "updated_at"}
    fields = [field.name for field in model._meta.fields if field.name not in excluded]
    fields.extend([field.name for field in model._meta.many_to_many])
    form_class = modelform_factory(model, fields=fields)
    if "published_at" in form_class.base_fields:
        form_class.base_fields["published_at"].widget = forms.DateTimeInput(
            attrs={"type": "datetime-local"}
        )
    return form_class
