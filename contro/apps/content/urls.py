from django.urls import path

from contro.apps.content import views

app_name = "content"

urlpatterns = [
    path("types/", views.content_type_list, name="type_list"),
    path("types/new/", views.content_type_create, name="type_create"),
    path("types/<int:pk>/edit/", views.content_type_edit, name="type_edit"),
    path("types/<int:pk>/fields/", views.field_list, name="field_list"),
    path("types/<int:pk>/fields/new/", views.field_create, name="field_create"),
    path("types/<int:pk>/fields/<int:field_pk>/edit/", views.field_edit, name="field_edit"),
    path("types/<int:pk>/entries/", views.entry_list, name="entry_list"),
    path("types/<int:pk>/entries/new/", views.entry_create, name="entry_create"),
    path("types/<int:pk>/entries/<int:entry_id>/edit/", views.entry_edit, name="entry_edit"),
    path("types/<int:pk>/entries/<int:entry_id>/delete/", views.entry_delete, name="entry_delete"),
    path("types/<int:pk>/entries/<int:entry_id>/publish/", views.entry_publish, name="entry_publish"),
    path("types/<int:pk>/entries/<int:entry_id>/unpublish/", views.entry_unpublish, name="entry_unpublish"),
]
