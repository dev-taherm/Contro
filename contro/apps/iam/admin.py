from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from contro.apps.iam.forms import UserChangeForm, UserCreationForm
from contro.apps.iam.models import ApiToken, ObjectPermission, Role, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    model = User
    add_form = UserCreationForm
    form = UserChangeForm
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "roles")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Profile", {"fields": ("username", "first_name", "last_name")}),
        ("Roles", {"fields": ("roles",)}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2", "is_staff", "is_superuser"),
            },
        ),
    )


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")
    filter_horizontal = ("permissions",)


@admin.register(ObjectPermission)
class ObjectPermissionAdmin(admin.ModelAdmin):
    list_display = ("permission", "user", "role", "content_type", "object_id")
    list_filter = ("content_type", "permission")
    search_fields = ("object_id",)


@admin.register(ApiToken)
class ApiTokenAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "token_prefix", "is_active", "expires_at", "last_used_at")
    list_filter = ("is_active",)
    search_fields = ("name", "token_prefix", "user__email")
    filter_horizontal = ("permissions",)
