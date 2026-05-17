from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from django.utils import timezone

from apps.agent.graph import build_research_graph
from apps.agent.tools.database_tools import emit_event, model_has_field, set_model_value
from apps.research.models import ResearchSession


@dataclass
class AgentRunResult:
    session_id: str
    status: str
    final_answer: str = ""
    references: list[dict[str, Any]] = field(default_factory=list)
    error_message: str = ""


class AgentRunner:
    def __init__(self):
        self.graph = build_research_graph()

    def run(self, session_id: str) -> AgentRunResult:
        session = ResearchSession.objects.select_related("repository").get(id=session_id)

        try:
            set_model_value(session, "status", "running")
            set_model_value(session, "started_at", timezone.now())
            set_model_value(session, "error_message", "")
            session.save()

            emit_event(
                session_id=str(session.id),
                event_type="agent_started",
                title="Agent started",
                message="LangGraph source-code research workflow has started.",
                payload={
                    "repository_id": str(session.repository_id),
                    "question": session.question,
                    "llm_provider": getattr(session, "llm_provider", ""),
                    "model_name": getattr(session, "model_name", ""),
                },
            )

            result = self.graph.invoke({"session_id": str(session.id)})

            session.refresh_from_db()

            update_fields = []

            if model_has_field(ResearchSession, "total_tool_calls"):
                session.total_tool_calls = (
                    session.tool_calls.count()
                    if hasattr(session, "tool_calls")
                    else 0
                )
                update_fields.append("total_tool_calls")

            if model_has_field(ResearchSession, "total_findings"):
                session.total_findings = (
                    session.findings.count()
                    if hasattr(session, "findings")
                    else 0
                )
                update_fields.append("total_findings")

            if update_fields:
                update_fields.append("updated_at")
                session.save(update_fields=update_fields)

            return AgentRunResult(
                session_id=str(session.id),
                status=getattr(session, "status", "completed"),
                final_answer=getattr(session, "final_answer", ""),
                references=result.get("answer_references", []),
            )

        except Exception as exc:
            set_model_value(session, "status", "failed")
            set_model_value(session, "error_message", str(exc))
            set_model_value(session, "completed_at", timezone.now())
            session.save()

            emit_event(
                session_id=str(session.id),
                event_type="session_failed",
                title="Research failed",
                message=str(exc),
                payload={"error": str(exc)},
            )

            return AgentRunResult(
                session_id=str(session.id),
                status="failed",
                error_message=str(exc),
            )