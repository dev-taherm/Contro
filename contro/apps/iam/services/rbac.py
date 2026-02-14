from __future__ import annotations

from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType

from contro.apps.iam.models import ObjectPermission, Role, User


def resolve_permission(perm: str) -> Permission | None:
    if not perm or "." not in perm:
        return None
    app_label, codename = perm.split(".", 1)
    try:
        return Permission.objects.get(content_type__app_label=app_label, codename=codename)
    except Permission.DoesNotExist:
        return None


def assign_role(user: User, role: Role) -> None:
    user.roles.add(role)


def revoke_role(user: User, role: Role) -> None:
    user.roles.remove(role)


def grant_role_permission(role: Role, perm: str) -> None:
    perm_obj = resolve_permission(perm)
    if not perm_obj:
        raise ValueError("Permission not found")
    role.permissions.add(perm_obj)


def revoke_role_permission(role: Role, perm: str) -> None:
    perm_obj = resolve_permission(perm)
    if not perm_obj:
        return
    role.permissions.remove(perm_obj)


def grant_object_permission(subject, perm: str, obj) -> ObjectPermission:
    perm_obj = resolve_permission(perm)
    if not perm_obj:
        raise ValueError("Permission not found")
    content_type = ContentType.objects.get_for_model(obj)
    object_id = str(obj.pk)
    return ObjectPermission.objects.create(
        permission=perm_obj,
        user=subject if isinstance(subject, User) else None,
        role=subject if isinstance(subject, Role) else None,
        content_type=content_type,
        object_id=object_id,
    )


def has_permission(user: User, perm: str, obj=None) -> bool:
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True

    perm_obj = resolve_permission(perm)
    if not perm_obj:
        return False

    if obj is None:
        return Role.objects.filter(users=user, permissions=perm_obj).exists()

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
