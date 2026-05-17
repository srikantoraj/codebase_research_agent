from django.db.models import Q

from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog


class ResearchSessionSelector:
    @staticmethod
    def base_queryset():
        return (
            ResearchSession.objects.select_related("repository")
            .prefetch_related("findings", "tool_calls", "events")
            .all()
        )

    @classmethod
    def list_sessions(cls, filters=None):
        filters = filters or {}
        queryset = cls.base_queryset()

        status = filters.get("status")
        repository_id = filters.get("repository_id")
        query = (filters.get("q") or "").strip()

        if status:
            queryset = queryset.filter(status=status)
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)
        if query:
            queryset = queryset.filter(
                Q(question__icontains=query)
                | Q(final_answer__icontains=query)
                | Q(repository__name__icontains=query)
                | Q(repository__owner__icontains=query)
            )

        return queryset.order_by("-created_at")

    @classmethod
    def get_session(cls, session_id):
        return cls.base_queryset().get(id=session_id)

    @staticmethod
    def sessions_for_repository(repository_id):
        return (
            ResearchSession.objects.filter(repository_id=repository_id)
            .select_related("repository")
            .order_by("-created_at")
        )


class FindingSelector:
    @staticmethod
    def for_session(session_id):
        return Finding.objects.filter(session_id=session_id).order_by("created_at")

    @staticmethod
    def previous_for_repository(repository, limit=20):
        return (
            Finding.objects.filter(repository=repository)
            .select_related("session", "repository")
            .order_by("-created_at")[:limit]
        )


class ToolCallLogSelector:
    @staticmethod
    def for_session(session_id):
        return ToolCallLog.objects.filter(session_id=session_id).order_by("created_at")


class AgentEventSelector:
    @staticmethod
    def public_for_session(session_id):
        return AgentEvent.objects.filter(session_id=session_id, is_public=True).order_by("created_at")
