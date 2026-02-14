from __future__ import annotations

from rest_framework import serializers


_SERIALIZER_CACHE = {}


def get_serializer_for_model(model_class: type):
    model_name = model_class._meta.model_name
    if model_name in _SERIALIZER_CACHE:
        return _SERIALIZER_CACHE[model_name]

    class Meta:
        model = model_class
        fields = "__all__"

    serializer_class = type(
        f"{model_class.__name__}Serializer",
        (serializers.ModelSerializer,),
        {"Meta": Meta},
    )
    _SERIALIZER_CACHE[model_name] = serializer_class
    return serializer_class
