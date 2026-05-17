from __future__ import annotations

from apps.agent.state import ResearchAgentState
from apps.agent.tools.database_tools import emit_event, execute_logged_tool, get_previous_findings, list_past_sessions
from apps.research.models import ResearchSession


def load_context_node(state: ResearchAgentState) -> ResearchAgentState:
    session = ResearchSession.objects.select_related("repository").get(id=state["session_id"])
    repository = session.repository
    options = getattr(session, "options", None) or state.get("options", {}) or {}

    emit_event(str(session.id), "session_started", "Research session started", session.question, step_number=1)

    previous_findings = execute_logged_tool(
        str(session.id),
        "get_previous_findings",
        {"repository_id": str(repository.id), "limit": 15},
        get_previous_findings,
    )
    past_sessions = execute_logged_tool(
        str(session.id),
        "list_past_sessions",
        {"repository_id": str(repository.id), "limit": 8},
        list_past_sessions,
    )

    repo_name = getattr(repository, "display_name", "") or f"{getattr(repository, 'owner', '')}/{getattr(repository, 'name', '')}".strip("/")

    state.update({
        "repository_id": str(repository.id),
        "repository_name": repo_name or getattr(repository, "name", "repository"),
        "repo_path": repository.local_path,
        "question": session.question,
        "options": options,
        "llm_provider": str(options.get("llm_provider") or "openai").lower(),
        "model_name": str(options.get("model_name") or ""),
        "max_steps": int(options.get("max_steps") or 8),
        "max_files_to_read": int(options.get("max_files_to_read") or 8),
        "previous_findings": previous_findings,
        "past_sessions": past_sessions,
        "search_results": [],
        "files_read": [],
        "findings": [],
        "tool_calls": [],
        "events": [],
        "answer_references": [],
    })
    return state
