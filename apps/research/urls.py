from django.urls import path

from apps.research.views import (
    RepositoryResearchSessionsAPIView,
    ResearchHealthAPIView,
    ResearchSessionCancelAPIView,
    ResearchSessionDetailAPIView,
    ResearchSessionEventsAPIView,
    ResearchSessionFindingsAPIView,
    ResearchSessionListCreateAPIView,
    ResearchSessionRunAPIView,
    ResearchSessionToolCallsAPIView,
)

app_name = "research"

urlpatterns = [
    path("health/", ResearchHealthAPIView.as_view(), name="research-health"),
    path("sessions/", ResearchSessionListCreateAPIView.as_view(), name="session-list-create"),
    path("sessions/<uuid:id>/", ResearchSessionDetailAPIView.as_view(), name="session-detail"),
    path("sessions/<uuid:id>/run/", ResearchSessionRunAPIView.as_view(), name="session-run"),
    path("sessions/<uuid:id>/cancel/", ResearchSessionCancelAPIView.as_view(), name="session-cancel"),
    path("sessions/<uuid:session_id>/findings/", ResearchSessionFindingsAPIView.as_view(), name="session-findings"),
    path("sessions/<uuid:session_id>/tool-calls/", ResearchSessionToolCallsAPIView.as_view(), name="session-tool-calls"),
    path("sessions/<uuid:session_id>/events/", ResearchSessionEventsAPIView.as_view(), name="session-events"),
    path("repositories/<uuid:repository_id>/sessions/", RepositoryResearchSessionsAPIView.as_view(), name="repository-sessions"),
]
