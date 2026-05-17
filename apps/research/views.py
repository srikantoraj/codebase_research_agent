from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.repositories.models import Repository
from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog
from apps.research.selectors import (
    AgentEventSelector,
    FindingSelector,
    ResearchSessionSelector,
    ToolCallLogSelector,
)
from apps.research.serializers import (
    AgentEventSerializer,
    FindingSerializer,
    ResearchSessionDetailSerializer,
    ResearchSessionListSerializer,
    RunResearchSessionSerializer,
    SessionFilterSerializer,
    StartResearchSessionSerializer,
    ToolCallLogSerializer,
)
from apps.research.services import ResearchService, ResearchServiceError


class ResearchSessionListCreateAPIView(generics.ListCreateAPIView):
    def get_queryset(self):
        filter_serializer = SessionFilterSerializer(data=self.request.query_params)
        filter_serializer.is_valid(raise_exception=True)
        return ResearchSessionSelector.list_sessions(filter_serializer.validated_data)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return StartResearchSessionSerializer
        return ResearchSessionListSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = ResearchService.start_session(
                repository_id=serializer.validated_data.get("repository_id"),
                repo_url=serializer.validated_data.get("repo_url"),
                local_path=serializer.validated_data.get("local_path"),
                question=serializer.validated_data["question"],
                options=serializer.validated_data.get("options") or {},
                sync_repository=serializer.validated_data.get("sync_repository", True),
                run_agent=serializer.validated_data.get("run_agent", True),
            )
        except Exception as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = ResearchSessionDetailSerializer(session, context=self.get_serializer_context())
        return Response(output.data, status=status.HTTP_201_CREATED)


class ResearchSessionDetailAPIView(generics.RetrieveAPIView):
    serializer_class = ResearchSessionDetailSerializer
    lookup_field = "id"

    def get_queryset(self):
        return ResearchSessionSelector.base_queryset()

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class ResearchSessionRunAPIView(APIView):
    def post(self, request, id):
        serializer = RunResearchSessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            session = ResearchSessionSelector.get_session(id)
        except ResearchSession.DoesNotExist:
            return Response({"detail": "Research session not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            session = ResearchService.run_existing_session(
                session=session,
                force=serializer.validated_data.get("force", False),
                options=serializer.validated_data.get("options") or {},
            )
        except ResearchServiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        output = ResearchSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class ResearchSessionCancelAPIView(APIView):
    def post(self, request, id):
        try:
            session = ResearchSessionSelector.get_session(id)
        except ResearchSession.DoesNotExist:
            return Response({"detail": "Research session not found."}, status=status.HTTP_404_NOT_FOUND)

        session = ResearchService.cancel_session(session)
        output = ResearchSessionDetailSerializer(session, context={"request": request})
        return Response(output.data, status=status.HTTP_200_OK)


class RepositoryResearchSessionsAPIView(generics.ListAPIView):
    serializer_class = ResearchSessionListSerializer

    def get_queryset(self):
        return ResearchSessionSelector.sessions_for_repository(self.kwargs["repository_id"])

    def list(self, request, *args, **kwargs):
        if not Repository.objects.filter(id=kwargs["repository_id"]).exists():
            return Response({"detail": "Repository not found."}, status=status.HTTP_404_NOT_FOUND)
        return super().list(request, *args, **kwargs)


class ResearchSessionFindingsAPIView(generics.ListAPIView):
    serializer_class = FindingSerializer

    def get_queryset(self):
        return FindingSelector.for_session(self.kwargs["session_id"])


class ResearchSessionToolCallsAPIView(generics.ListAPIView):
    serializer_class = ToolCallLogSerializer

    def get_queryset(self):
        return ToolCallLogSelector.for_session(self.kwargs["session_id"])


class ResearchSessionEventsAPIView(generics.ListAPIView):
    serializer_class = AgentEventSerializer

    def get_queryset(self):
        return AgentEventSelector.public_for_session(self.kwargs["session_id"])


class ResearchHealthAPIView(APIView):
    def get(self, request):
        return Response(
            {
                "status": "ok",
                "app": "research",
                "models": ["ResearchSession", "Finding", "ToolCallLog", "AgentEvent"],
                "endpoints": {
                    "sessions": "/api/research/sessions/",
                    "session_detail": "/api/research/sessions/<uuid>/",
                    "repo_sessions": "/api/research/repositories/<uuid>/sessions/",
                },
            }
        )
