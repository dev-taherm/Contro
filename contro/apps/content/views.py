from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from contro.apps.content.forms import ContentFieldForm, ContentTypeForm, content_entry_form
from contro.apps.content.models import ContentFieldDefinition, ContentTypeDefinition
from contro.apps.content.services.schema import get_dynamic_model, sync_schema
from contro.apps.content.services.hooks import run_hooks


def _check_perm(user, perm: str, obj=None) -> None:
    if not user.has_perm(perm, obj=obj):
        raise PermissionDenied


@login_required
@require_http_methods(["GET"])
def content_type_list(request):
    _check_perm(request.user, "content.view_contenttypedefinition")
    content_types = ContentTypeDefinition.objects.all()
    return render(request, "content/type_list.html", {"content_types": content_types})


@login_required
@require_http_methods(["GET", "POST"])
def content_type_create(request):
    _check_perm(request.user, "content.add_contenttypedefinition")
    form = ContentTypeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        content_type = form.save()
        try:
            sync_schema(content_type)
            messages.success(request, "Content type created.")
            return redirect("content:type_edit", pk=content_type.pk)
        except Exception as exc:
            content_type.delete()
            messages.error(request, f"Schema sync failed: {exc}")
    return render(request, "content/type_form.html", {"form": form, "mode": "create"})


@login_required
@require_http_methods(["GET", "POST"])
def content_type_edit(request, pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    _check_perm(request.user, "content.change_contenttypedefinition", obj=content_type)
    form = ContentTypeForm(request.POST or None, instance=content_type)
    if request.method == "POST" and form.is_valid():
        content_type = form.save()
        try:
            sync_schema(content_type)
            messages.success(request, "Content type updated.")
            return redirect("content:type_edit", pk=content_type.pk)
        except Exception as exc:
            messages.error(request, f"Schema sync failed: {exc}")
    return render(
        request,
        "content/type_form.html",
        {"form": form, "mode": "edit", "content_type": content_type},
    )


@login_required
@require_http_methods(["GET"])
def field_list(request, pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    _check_perm(request.user, "content.view_contentfielddefinition")
    fields = content_type.fields.all()
    return render(
        request,
        "content/field_list.html",
        {"content_type": content_type, "fields": fields},
    )


@login_required
@require_http_methods(["GET", "POST"])
def field_create(request, pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    _check_perm(request.user, "content.add_contentfielddefinition")
    form = ContentFieldForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        field = form.save(commit=False)
        field.content_type = content_type
        field.save()
        try:
            sync_schema(content_type)
            messages.success(request, "Field created.")
            return redirect("content:field_list", pk=content_type.pk)
        except Exception as exc:
            field.delete()
            messages.error(request, f"Schema sync failed: {exc}")
    return render(
        request,
        "content/field_form.html",
        {"form": form, "mode": "create", "content_type": content_type},
    )


@login_required
@require_http_methods(["GET", "POST"])
def field_edit(request, pk: int, field_pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    field = get_object_or_404(ContentFieldDefinition, pk=field_pk, content_type=content_type)
    _check_perm(request.user, "content.change_contentfielddefinition", obj=field)
    form = ContentFieldForm(request.POST or None, instance=field)
    if request.method == "POST" and form.is_valid():
        form.save()
        try:
            sync_schema(content_type)
            messages.success(request, "Field updated.")
            return redirect("content:field_list", pk=content_type.pk)
        except Exception as exc:
            messages.error(request, f"Schema sync failed: {exc}")
    return render(
        request,
        "content/field_form.html",
        {"form": form, "mode": "edit", "content_type": content_type, "field": field},
    )


@login_required
@require_http_methods(["GET"])
def entry_list(request, pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    perm = f"content.view_{model._meta.model_name}"
    _check_perm(request.user, perm)

    entries = model.objects.all().order_by("-id")
    fields = content_type.fields.all()
    return render(
        request,
        "content/entry_list.html",
        {"content_type": content_type, "entries": entries, "fields": fields},
    )


@login_required
@require_http_methods(["GET", "POST"])
def entry_create(request, pk: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    perm = f"content.add_{model._meta.model_name}"
    _check_perm(request.user, perm)

    EntryForm = content_entry_form(content_type)
    form = EntryForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        run_hooks("pre_create", data=form.cleaned_data, request=request)
        entry = form.save()
        run_hooks("post_create", instance=entry, request=request)
        messages.success(request, "Entry created.")
        return redirect("content:entry_edit", pk=content_type.pk, entry_id=entry.pk)
    return render(
        request,
        "content/entry_form.html",
        {"form": form, "content_type": content_type, "mode": "create"},
    )


@login_required
@require_http_methods(["GET", "POST"])
def entry_edit(request, pk: int, entry_id: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    entry = get_object_or_404(model, pk=entry_id)

    perm = f"content.change_{model._meta.model_name}"
    _check_perm(request.user, perm, obj=entry)

    EntryForm = content_entry_form(content_type)
    form = EntryForm(request.POST or None, instance=entry)
    if request.method == "POST" and form.is_valid():
        run_hooks("pre_update", instance=entry, data=form.cleaned_data, request=request)
        entry = form.save()
        run_hooks("post_update", instance=entry, request=request)
        messages.success(request, "Entry updated.")
        return redirect("content:entry_edit", pk=content_type.pk, entry_id=entry.pk)

    return render(
        request,
        "content/entry_form.html",
        {"form": form, "content_type": content_type, "mode": "edit", "entry": entry},
    )


@login_required
@require_http_methods(["POST"])
def entry_delete(request, pk: int, entry_id: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    entry = get_object_or_404(model, pk=entry_id)

    perm = f"content.delete_{model._meta.model_name}"
    _check_perm(request.user, perm, obj=entry)

    run_hooks("pre_delete", instance=entry, request=request)
    entry.delete()
    run_hooks("post_delete", instance=entry, request=request)
    messages.success(request, "Entry deleted.")
    return redirect("content:entry_list", pk=content_type.pk)


@login_required
@require_http_methods(["POST"])
def entry_publish(request, pk: int, entry_id: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    entry = get_object_or_404(model, pk=entry_id)

    perm = f"content.change_{model._meta.model_name}"
    _check_perm(request.user, perm, obj=entry)

    run_hooks("pre_publish", instance=entry, request=request)
    entry.publish()
    entry.save()
    run_hooks("post_publish", instance=entry, request=request)
    messages.success(request, "Entry published.")
    return redirect("content:entry_edit", pk=content_type.pk, entry_id=entry.pk)


@login_required
@require_http_methods(["POST"])
def entry_unpublish(request, pk: int, entry_id: int):
    content_type = get_object_or_404(ContentTypeDefinition, pk=pk)
    model = get_dynamic_model(content_type)
    entry = get_object_or_404(model, pk=entry_id)

    perm = f"content.change_{model._meta.model_name}"
    _check_perm(request.user, perm, obj=entry)

    run_hooks("pre_unpublish", instance=entry, request=request)
    entry.unpublish()
    entry.save()
    run_hooks("post_unpublish", instance=entry, request=request)
    messages.success(request, "Entry set to draft.")
    return redirect("content:entry_edit", pk=content_type.pk, entry_id=entry.pk)
