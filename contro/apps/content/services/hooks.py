from __future__ import annotations

from collections import defaultdict
from typing import Callable, Dict, List


HOOK_EVENTS = {
    "pre_create",
    "post_create",
    "pre_update",
    "post_update",
    "pre_delete",
    "post_delete",
    "pre_publish",
    "post_publish",
    "pre_unpublish",
    "post_unpublish",
}

_HOOKS: Dict[str, Dict[str, List[Callable]]] = defaultdict(lambda: defaultdict(list))


def register_hook(content_type_slug: str, event: str, func: Callable) -> None:
    if event not in HOOK_EVENTS:
        raise ValueError(f"Unsupported hook event: {event}")
    _HOOKS[event][content_type_slug].append(func)


def run_hooks(event: str, instance=None, **kwargs) -> None:
    if event not in HOOK_EVENTS:
        raise ValueError(f"Unsupported hook event: {event}")

    slug = None
    if instance is not None:
        slug = getattr(instance, "__content_type_slug__", None)

    for func in _HOOKS[event].get("*", []):
        func(instance=instance, **kwargs)
    if slug:
        for func in _HOOKS[event].get(slug, []):
            func(instance=instance, **kwargs)
