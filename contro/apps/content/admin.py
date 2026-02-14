from django.contrib import admin

from contro.apps.content.models import ContentFieldDefinition, ContentTypeDefinition


@admin.register(ContentTypeDefinition)
class ContentTypeDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "is_active", "updated_at")
    search_fields = ("name", "slug")
    list_filter = ("is_active",)


@admin.register(ContentFieldDefinition)
class ContentFieldDefinitionAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "field_type", "content_type", "required", "unique")
    list_filter = ("field_type", "content_type")
    search_fields = ("name", "slug")
