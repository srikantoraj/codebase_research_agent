from django.db import models

from apps.common.models import TimeStampedModel


class RepositorySourceType(models.TextChoices):
    GITHUB = "github", "GitHub"
    LOCAL = "local", "Local Path"


class RepositorySyncStatus(models.TextChoices):
    NOT_SYNCED = "not_synced", "Not Synced"
    SYNCING = "syncing", "Syncing"
    SYNCED = "synced", "Synced"
    FAILED = "failed", "Failed"


class Repository(TimeStampedModel):
    """
    Represents a repository that can be researched by the AI agent.

    A repository may come from a public GitHub URL or from a local path. The
    canonical_url field is intentionally nullable so local repositories do not
    need a fake URL.
    """

    source_type = models.CharField(
        max_length=20,
        choices=RepositorySourceType.choices,
        default=RepositorySourceType.GITHUB,
    )

    url = models.URLField(blank=True)
    canonical_url = models.URLField(unique=True, null=True, blank=True)
    owner = models.CharField(max_length=255, blank=True)
    name = models.CharField(max_length=255)

    default_branch = models.CharField(max_length=100, blank=True)
    current_branch = models.CharField(max_length=100, blank=True)
    current_commit_hash = models.CharField(max_length=64, blank=True)

    local_path = models.TextField(blank=True)
    source_file_count = models.PositiveIntegerField(default=0)

    sync_status = models.CharField(
        max_length=30,
        choices=RepositorySyncStatus.choices,
        default=RepositorySyncStatus.NOT_SYNCED,
    )
    sync_error = models.TextField(blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    last_analyzed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-updated_at"]
        indexes = [
            models.Index(fields=["source_type"]),
            models.Index(fields=["sync_status"]),
            models.Index(fields=["owner", "name"]),
            models.Index(fields=["last_synced_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["source_type", "local_path"],
                name="unique_repository_source_local_path",
                condition=models.Q(source_type=RepositorySourceType.LOCAL),
            )
        ]

    def __str__(self):
        if self.owner:
            return "%s/%s" % (self.owner, self.name)
        return self.name

    @property
    def display_name(self):
        if self.owner:
            return "%s/%s" % (self.owner, self.name)
        return self.name

    @property
    def is_synced(self):
        return self.sync_status == RepositorySyncStatus.SYNCED
