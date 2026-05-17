from rest_framework import serializers

from apps.repositories.models import Repository
from apps.repositories.services import RepositoryService


class RepositorySerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(read_only=True)
    is_synced = serializers.BooleanField(read_only=True)

    class Meta:
        model = Repository
        fields = [
            "id",
            "source_type",
            "url",
            "canonical_url",
            "owner",
            "name",
            "display_name",
            "default_branch",
            "current_branch",
            "current_commit_hash",
            "local_path",
            "source_file_count",
            "sync_status",
            "sync_error",
            "is_synced",
            "last_synced_at",
            "last_analyzed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RepositoryCreateSerializer(serializers.Serializer):
    repo_url = serializers.CharField(required=False, allow_blank=True)
    local_path = serializers.CharField(required=False, allow_blank=True)
    sync = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        repo_url = attrs.get("repo_url")
        local_path = attrs.get("local_path")

        if repo_url:
            attrs["repo_url"] = repo_url.strip()
        if local_path:
            attrs["local_path"] = local_path.strip()

        if not attrs.get("repo_url") and not attrs.get("local_path"):
            raise serializers.ValidationError("Either repo_url or local_path is required.")

        if attrs.get("repo_url") and attrs.get("local_path"):
            raise serializers.ValidationError("Provide either repo_url or local_path, not both.")

        return attrs

    def create(self, validated_data):
        return RepositoryService.get_or_create_from_input(
            repo_url=validated_data.get("repo_url"),
            local_path=validated_data.get("local_path"),
            sync=validated_data.get("sync", True),
        )


class RepositorySyncSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
