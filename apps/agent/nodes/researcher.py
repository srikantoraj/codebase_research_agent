from __future__ import annotations

from typing import Any

from apps.agent.state import ResearchAgentState
from apps.agent.tools.code_tools import read_around_match, search_code
from apps.agent.tools.database_tools import (
    emit_event,
    execute_logged_tool,
    save_finding,
)
from apps.research.models import ResearchSession


def evidence_snippet_from_read(file_data: dict[str, Any], max_chars: int = 1200) -> str:
    content = file_data.get("content", "") or ""

    if len(content) > max_chars:
        return content[:max_chars] + "\n... truncated ..."

    return content


def researcher_node(state: ResearchAgentState) -> ResearchAgentState:
    session_id = state["session_id"]
    session = ResearchSession.objects.select_related("repository").get(id=session_id)

    repo_path = session.repository.local_path
    max_files_to_read = int(
        (state.get("options") or {}).get("max_files_to_read")
        or getattr(session, "max_files_to_read", 8)
        or 8
    )

    max_file_chars = int(
        (state.get("options") or {}).get("max_file_chars")
        or 16000
    )

    search_terms = state.get("search_terms") or [session.question]
    likely_paths = state.get("likely_paths") or []

    source_first = bool(state.get("source_first", True))
    include_docs = bool(state.get("include_docs", False))
    include_tests = bool(state.get("include_tests", False))

    emit_event(
        session_id=session_id,
        event_type="research_started",
        title="Research started",
        message="Searching implementation source files first.",
        payload={
            "search_terms": search_terms,
            "source_first": source_first,
            "include_docs": include_docs,
            "include_tests": include_tests,
        },
    )

    all_matches: list[dict[str, Any]] = []
    seen_locations = set()

    for query in search_terms:
        output = execute_logged_tool(
            session_id=session_id,
            tool_name="search_code",
            input_payload={
                "repo_path": repo_path,
                "query": query,
                "max_results": 12,
                "source_first": source_first,
                "include_docs": include_docs,
                "include_tests": include_tests,
                "likely_paths": likely_paths,
            },
            func=search_code,
        )

        for match in output.get("results", []):
            key = (
                match.get("file_path"),
                match.get("line_number"),
                match.get("line"),
            )

            if key in seen_locations:
                continue

            seen_locations.add(key)
            match["query"] = query
            all_matches.append(match)

    all_matches = sorted(
        all_matches,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )

    selected_matches = all_matches[:max_files_to_read]

    files_read: list[dict[str, Any]] = []
    findings: list[dict[str, Any]] = []
    references: list[dict[str, Any]] = []

    for match in selected_matches:
        file_data = execute_logged_tool(
            session_id=session_id,
            tool_name="read_around_match",
            input_payload={
                "repo_path": repo_path,
                "match": match,
                "before": 35,
                "after": 90,
                "max_chars": max_file_chars,
            },
            func=read_around_match,
        )

        files_read.append(file_data)

        note = (
            "Relevant implementation match for query '{query}' near line {line}: {source_line}"
        ).format(
            query=match.get("query", ""),
            line=match.get("line_number", ""),
            source_line=(match.get("line", "") or "")[:250],
        )

        finding = execute_logged_tool(
            session_id=session_id,
            tool_name="save_finding",
            input_payload={
                "session_id": session_id,
                "file_path": match.get("file_path", ""),
                "function_name": match.get("function_name", ""),
                "line_start": match.get("line_number"),
                "line_end": match.get("line_number"),
                "note": note,
                "evidence_snippet": evidence_snippet_from_read(file_data),
                "confidence": match.get("score", 0.75),
                "metadata": {
                    "query": match.get("query"),
                    "source_first": source_first,
                },
            },
            func=save_finding,
        )

        findings.append(finding)

        references.append(
            {
                "file_path": finding.get("file_path"),
                "line_start": finding.get("line_start"),
                "line_end": finding.get("line_end"),
                "function_name": finding.get("function_name", ""),
            }
        )

    state["matches"] = selected_matches
    state["files_read"] = files_read
    state["findings"] = findings
    state["answer_references"] = references

    emit_event(
        session_id=session_id,
        event_type="research_completed",
        title="Research evidence collected",
        message="Source evidence was collected for final answer generation.",
        payload={
            "matches": len(selected_matches),
            "files_read": len(files_read),
            "findings": len(findings),
        },
    )

    return state