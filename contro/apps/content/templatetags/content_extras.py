from django import template

register = template.Library()


@register.filter
def attr(obj, name):
    value = getattr(obj, name)
    if hasattr(value, "all"):
        return ", ".join(str(item) for item in value.all())
    return value
