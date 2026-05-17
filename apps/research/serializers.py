from rest_framework import serializers

from apps.repositories.models import Repository
from apps.repositories.serializers import RepositorySerializer
from apps.research.enums import ResearchSessionStatus
from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog


class StartResearchSessionSerializer(serializers.Serializer):
    repository_id = serializers.UUIDField(required=False)
    repo_url = serializers.CharField(required=False, allow_blank=True)
    local_path = serializers.CharField(required=False, allow_blank=True)
    question = serializers.CharField(max_length=4000)

    sync_repository = serializers.BooleanField(required=False, default=True)
    run_agent = serializers.BooleanField(required=False, default=True)
    options = serializers.DictField(required=False, default=dict)

    def validate_question(self, value):
        cleaned = value.strip()
        if len(cleaned) < 5:
            raise serializers.ValidationError("Question is too short.")
        return cleaned

    def validate(self, attrs):
        repository_id = attrs.get("repository_id")
        repo_url = (attrs.get("repo_url") or "").strip()
        local_path = (attrs.get("local_path") or "").strip()

        supplied_sources = [bool(repository_id), bool(repo_url), bool(local_path)]
        if sum(supplied_sources) != 1:
            raise serializers.ValidationError(
                "Provide exactly one of repository_id, repo_url, or local_path."
            )

        if repository_id and not Repository.objects.filter(id=repository_id).exists():
            raise serializers.ValidationError({"repository_id": "Repository not found."})

        if repo_url:
            attrs["repo_url"] = repo_url
        if local_path:
            attrs["local_path"] = local_path

        options = attrs.get("options") or {}
        max_steps = int(options.get("max_steps", 8) or 8)
        if max_steps < 1 or max_steps > 20:
            raise serializers.ValidationError({"options": "max_steps must be between 1 and 20."})
        options["max_steps"] = max_steps
        attrs["options"] = options
        return attrs


class RunResearchSessionSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
    options = serializers.DictField(required=False, default=dict)


class FindingSerializer(serializers.ModelSerializer):
    reference = serializers.DictField(read_only=True)

    class Meta:
        model = Finding
        fields = [
            "id",
            "source",
            "file_path",
            "symbol_name",
            "symbol_type",
            "line_start",
            "line_end",
            "note",
            "evidence_snippet",
            "confidence",
            "metadata",
            "reference",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ToolCallLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToolCallLog
        fields = [
            "id",
            "tool_name",
            "tool_type",
            "status",
            "step_number",
            "input_payload",
            "output_payload",
            "error_message",
            "duration_ms",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AgentEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentEvent
        fields = [
            "id",
            "event_type",
            "title",
            "message",
            "payload",
            "step_number",
            "is_public",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ResearchSessionListSerializer(serializers.ModelSerializer):
    repository = RepositorySerializer(read_only=True)
    websocket_url = serializers.SerializerMethodField()

    class Meta:
        model = ResearchSession
        fields = [
            "id",
            "repository",
            "question",
            "status",
            "error_message",
            "total_tool_calls",
            "total_findings",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "websocket_url",
        ]
        read_only_fields = fields

    def get_websocket_url(self, obj):
        request = self.context.get("request")
        if not request:
            return "/ws/research/sessions/%s/" % obj.id
        scheme = "wss" if request.is_secure() else "ws"
        return "%s://%s/ws/research/sessions/%s/" % (
            scheme,
            request.get_host(),
            obj.id,
        )


class ResearchSessionDetailSerializer(serializers.ModelSerializer):
    repository = RepositorySerializer(read_only=True)
    findings = FindingSerializer(many=True, read_only=True)
    tool_calls = ToolCallLogSerializer(many=True, read_only=True)
    events = AgentEventSerializer(many=True, read_only=True)
    websocket_url = serializers.SerializerMethodField()

    class Meta:
        model = ResearchSession
        fields = [
            "id",
            "repository",
            "question",
            "status",
            "final_answer",
            "error_message",
            "options",
            "answer_references",
            "llm_provider",
            "model_name",
            "max_steps",
            "current_step",
            "input_tokens",
            "output_tokens",
            "total_tool_calls",
            "total_findings",
            "started_at",
            "completed_at",
            "created_at",
            "updated_at",
            "websocket_url",
            "findings",
            "tool_calls",
            "events",
        ]
        read_only_fields = fields

    def get_websocket_url(self, obj):
        request = self.context.get("request")
        if not request:
            return "/ws/research/sessions/%s/" % obj.id
        scheme = "wss" if request.is_secure() else "ws"
        return "%s://%s/ws/research/sessions/%s/" % (
            scheme,
            request.get_host(),
            obj.id,
        )


class ResearchSessionCreatedSerializer(ResearchSessionDetailSerializer):
    """Alias serializer to make view intent explicit."""


class ResearchSessionStatusSerializer(serializers.ModelSerializer):
    websocket_url = serializers.SerializerMethodField()

    class Meta:
        model = ResearchSession
        fields = [
            "id",
            "status",
            "error_message",
            "total_tool_calls",
            "total_findings",
            "started_at",
            "completed_at",
            "websocket_url",
        ]
        read_only_fields = fields

    def get_websocket_url(self, obj):
        request = self.context.get("request")
        if not request:
            return "/ws/research/sessions/%s/" % obj.id
        scheme = "wss" if request.is_secure() else "ws"
        return "%s://%s/ws/research/sessions/%s/" % (
            scheme,
            request.get_host(),
            obj.id,
        )


class SessionFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=ResearchSessionStatus.choices,
        required=False,
    )
    repository_id = serializers.UUIDField(required=False)
    q = serializers.CharField(required=False, allow_blank=True)
