from django.urls import path

from apps.repositories.views import (
    RepositoryDetailAPIView,
    RepositoryListCreateAPIView,
    RepositorySyncAPIView,
)

app_name = "repositories"

urlpatterns = [
    path("", RepositoryListCreateAPIView.as_view(), name="repository-list-create"),
    path("<uuid:id>/", RepositoryDetailAPIView.as_view(), name="repository-detail"),
    path("<uuid:id>/sync/", RepositorySyncAPIView.as_view(), name="repository-sync"),
]
