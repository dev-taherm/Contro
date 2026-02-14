from __future__ import annotations

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from contro.apps.iam.models import ObjectPermission, Role


class RolePermissionBackend:
    """Adds role-based and object-level permissions on top of Django's auth backend."""

    def has_perm(self, user_obj, perm, obj=None):
        if not user_obj or not user_obj.is_active:
            return False
        if user_obj.is_superuser:
            return True

        perm_obj = self._resolve_permission(perm)
        if not perm_obj:
            return False

        if obj is None:
            return self._user_has_role_permission(user_obj, perm_obj)

        return self._user_has_object_permission(user_obj, perm_obj, obj)

    def has_module_perms(self, user_obj, app_label):
        if not user_obj or not user_obj.is_active:
            return False
        if user_obj.is_superuser:
            return True
        return (
            user_obj.roles.filter(permissions__content_type__app_label=app_label).exists()
            or ObjectPermission.objects.filter(
                role__in=user_obj.roles.all(),
                permission__content_type__app_label=app_label,
            ).exists()
        )

    @staticmethod
    def _resolve_permission(perm):
        if not perm or "." not in perm:
            return None
        app_label, codename = perm.split(".", 1)
        try:
            return Permission.objects.get(content_type__app_label=app_label, codename=codename)
        except Permission.DoesNotExist:
            return None

    @staticmethod
    def _user_has_role_permission(user, perm_obj: Permission) -> bool:
        return Role.objects.filter(users=user, permissions=perm_obj).exists()

    @staticmethod
    def _user_has_object_permission(user, perm_obj: Permission, obj) -> bool:
        content_type = ContentType.objects.get_for_model(obj)
        object_id = str(obj.pk)

        if ObjectPermission.objects.filter(
            permission=perm_obj,
            user=user,
            content_type=content_type,
            object_id=object_id,
        ).exists():
            return True

        return ObjectPermission.objects.filter(
            permission=perm_obj,
            role__in=user.roles.all(),
            content_type=content_type,
            object_id=object_id,
        ).exists()
