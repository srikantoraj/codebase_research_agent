from django.contrib import admin, messages

from apps.repositories.models import Repository
from apps.repositories.services import RepositoryService


@admin.register(Repository)
class RepositoryAdmin(admin.ModelAdmin):
    list_display = [
        "display_name",
        "source_type",
        "sync_status",
        "source_file_count",
        "current_branch",
        "last_synced_at",
        "updated_at",
    ]
    list_filter = ["source_type", "sync_status", "last_synced_at"]
    search_fields = ["url", "canonical_url", "owner", "name", "local_path"]
    readonly_fields = [
        "id",
        "display_name",
        "created_at",
        "updated_at",
        "last_synced_at",
        "last_analyzed_at",
        "current_branch",
        "current_commit_hash",
        "source_file_count",
        "sync_error",
    ]
    actions = ["sync_selected_repositories"]

    fieldsets = (
        (
            "Repository",
            {
                "fields": (
                    "id",
                    "source_type",
                    "url",
                    "canonical_url",
                    "owner",
                    "name",
                    "display_name",
                    "local_path",
                )
            },
        ),
        (
            "Sync State",
            {
                "fields": (
                    "sync_status",
                    "sync_error",
                    "default_branch",
                    "current_branch",
                    "current_commit_hash",
                    "source_file_count",
                    "last_synced_at",
                    "last_analyzed_at",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    @admin.action(description="Sync selected repositories")
    def sync_selected_repositories(self, request, queryset):
        synced = 0
        failed = 0

        for repository in queryset:
            try:
                RepositoryService.sync(repository)
                synced += 1
            except Exception as exc:  # pragma: no cover - admin feedback only
                failed += 1
                self.message_user(
                    request,
                    "Failed to sync %s: %s" % (repository.display_name, exc),
                    level=messages.ERROR,
                )

        if synced:
            self.message_user(
                request,
                "Successfully synced %s repository/repositories." % synced,
                level=messages.SUCCESS,
            )
        if failed:
            self.message_user(
                request,
                "%s repository/repositories failed to sync." % failed,
                level=messages.WARNING,
            )
