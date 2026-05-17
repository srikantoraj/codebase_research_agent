import tempfile
from pathlib import Path

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.repositories.models import Repository, RepositorySourceType, RepositorySyncStatus
from apps.research.enums import ResearchSessionStatus
from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog
from apps.research.services import ResearchService


@pytest.mark.django_db
def test_create_research_session_without_running_agent():
    with tempfile.TemporaryDirectory() as tmpdir:
        repository = Repository.objects.create(
            source_type=RepositorySourceType.LOCAL,
            name="sample",
            local_path=tmpdir,
            sync_status=RepositorySyncStatus.SYNCED,
        )

        session = ResearchService.start_session(
            repository_id=repository.id,
            question="Where is dependency injection implemented?",
            sync_repository=False,
            run_agent=False,
        )

        assert session.status == ResearchSessionStatus.PENDING
        assert session.repository == repository
        assert AgentEvent.objects.filter(session=session).exists()


@pytest.mark.django_db
def test_starter_research_execution_saves_findings_and_tool_logs():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "app.py").write_text(
            "def dependency_injection():\n    return 'dependency injection system'\n",
            encoding="utf-8",
        )
        repository = Repository.objects.create(
            source_type=RepositorySourceType.LOCAL,
            name="sample",
            local_path=tmpdir,
            sync_status=RepositorySyncStatus.SYNCED,
        )

        session = ResearchService.start_session(
            repository_id=repository.id,
            question="Where is dependency injection implemented?",
            sync_repository=False,
            run_agent=True,
        )

        assert session.status == ResearchSessionStatus.COMPLETED
        assert Finding.objects.filter(session=session).count() >= 1
        assert ToolCallLog.objects.filter(session=session).count() >= 1
        assert "Starter research completed" in session.final_answer


@pytest.mark.django_db
def test_research_session_api_creates_session():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        (root / "service.py").write_text("class RetryService:\n    pass\n", encoding="utf-8")
        repository = Repository.objects.create(
            source_type=RepositorySourceType.LOCAL,
            name="sample-api",
            local_path=tmpdir,
            sync_status=RepositorySyncStatus.SYNCED,
        )

        client = APIClient()
        response = client.post(
            "/api/research/sessions/",
            {
                "repository_id": str(repository.id),
                "question": "Where is RetryService implemented?",
                "sync_repository": False,
                "run_agent": True,
                "options": {"max_steps": 8},
            },
            format="json",
        )

        assert response.status_code == 201
        assert response.data["status"] == ResearchSessionStatus.COMPLETED
        assert len(response.data["tool_calls"]) >= 1
        assert len(response.data["events"]) >= 1
