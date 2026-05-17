from __future__ import annotations

from typing import Any, TypedDict


class ResearchAgentState(TypedDict, total=False):
    session_id: str
    repository_id: str
    repository_name: str
    repo_path: str
    question: str
    options: dict[str, Any]
    max_steps: int
    max_files_to_read: int
    llm_provider: str
    model_name: str
    previous_findings: list[dict[str, Any]]
    past_sessions: list[dict[str, Any]]
    search_terms: list[str]
    search_results: list[dict[str, Any]]
    files_read: list[dict[str, Any]]
    findings: list[dict[str, Any]]
    tool_calls: list[dict[str, Any]]
    events: list[dict[str, Any]]
    final_answer: str
    answer_references: list[dict[str, Any]]
    error_message: str
