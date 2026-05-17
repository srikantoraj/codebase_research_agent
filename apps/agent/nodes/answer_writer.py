from __future__ import annotations

import json

from django.utils import timezone

from apps.agent.llm import LLMNotConfiguredError, invoke_text_with_usage
from apps.agent.prompts import ANSWER_PROMPT, SYSTEM_PROMPT
from apps.agent.state import ResearchAgentState
from apps.agent.tools.database_tools import (
    emit_event,
    increment_token_usage,
    model_has_field,
    set_model_value,
)
from apps.research.models import ResearchSession


def build_evidence(state: ResearchAgentState) -> str:
    parts: list[str] = []

    for file_data in state.get("files_read", []):
        parts.append(
            "File: {file_path}\n"
            "Lines: {start_line}-{end_line}\n"
            "Content:\n{content}".format(
                file_path=file_data.get("file_path"),
                start_line=file_data.get("start_line"),
                end_line=file_data.get("end_line"),
                content=file_data.get("content", ""),
            )
        )

    return "\n\n---\n\n".join(parts)[:70000]


def fallback_answer(state: ResearchAgentState, reason: str = "") -> str:
    findings = state.get("findings", [])

    if not findings:
        return (
            "I could not gather enough source-code evidence to answer confidently. "
            "The repository was searched, but no strong implementation files were found."
            + (f"\n\nLLM note: {reason}" if reason else "")
        )

    lines = [
        "Initial evidence-based answer generated without an LLM.",
        "",
        "Relevant source evidence found:",
    ]

    for finding in findings:
        ref = f"{finding.get('file_path')}"

        if finding.get("line_start"):
            ref += f":{finding.get('line_start')}"

        if finding.get("function_name"):
            ref += f" ({finding.get('function_name')})"

        lines.append(f"- {ref} — {finding.get('note')}")

    if reason:
        lines.append("")
        lines.append(f"LLM note: {reason}")

    return "\n".join(lines)


def answer_writer_node(state: ResearchAgentState) -> ResearchAgentState:
    session_id = state["session_id"]

    emit_event(
        session_id=session_id,
        event_type="answer_started",
        title="Generating final answer",
        message="Writing final answer from collected source-code evidence.",
    )

    options = dict(state.get("options", {}) or {})

    if state.get("llm_provider"):
        options["llm_provider"] = state["llm_provider"]

    if state.get("model_name"):
        options["model_name"] = state["model_name"]

    session = ResearchSession.objects.get(id=session_id)

    try:
        prompt = ANSWER_PROMPT.format(
            question=state.get("question", ""),
            repository_name=state.get("repository_name", "repository"),
            evidence=build_evidence(state),
            previous_findings=json.dumps(
                state.get("previous_findings", []),
                indent=2,
                ensure_ascii=False,
            )[:5000],
        )

        llm_result = invoke_text_with_usage(
            system_prompt=SYSTEM_PROMPT,
            human_prompt=prompt,
            options=options,
        )

        final_answer = llm_result.content

        increment_token_usage(
            session_id=session_id,
            input_tokens=llm_result.input_tokens,
            output_tokens=llm_result.output_tokens,
        )

        emit_event(
            session_id=session_id,
            event_type="llm_completed",
            title="LLM answer generated",
            message="The final answer was generated using the configured LLM.",
            payload={
                "provider": llm_result.provider,
                "model_name": llm_result.model_name,
                "input_tokens": llm_result.input_tokens,
                "output_tokens": llm_result.output_tokens,
                "total_tokens": llm_result.total_tokens,
            },
        )

    except LLMNotConfiguredError as exc:
        final_answer = fallback_answer(state, reason=str(exc))

        emit_event(
            session_id=session_id,
            event_type="llm_skipped",
            title="LLM was not configured",
            message=str(exc),
            payload={"reason": str(exc)},
        )

    except Exception as exc:
        final_answer = fallback_answer(state, reason=f"LLM call failed: {exc}")

        emit_event(
            session_id=session_id,
            event_type="llm_failed",
            title="LLM call failed",
            message=str(exc),
            payload={"error": str(exc)},
        )

    session.refresh_from_db()

    set_model_value(session, "final_answer", final_answer)
    set_model_value(session, "answer_references", state.get("answer_references", []))
    set_model_value(session, "status", "completed")
    set_model_value(session, "completed_at", timezone.now())
    set_model_value(session, "error_message", "")

    if model_has_field(ResearchSession, "total_tool_calls"):
        session.total_tool_calls = (
            session.tool_calls.count()
            if hasattr(session, "tool_calls")
            else 0
        )

    if model_has_field(ResearchSession, "total_findings"):
        session.total_findings = (
            session.findings.count()
            if hasattr(session, "findings")
            else 0
        )

    session.save()

    state["final_answer"] = final_answer

    emit_event(
        session_id=session_id,
        event_type="session_completed",
        title="Research completed",
        message="Final answer is ready.",
        payload={
            "references": state.get("answer_references", []),
            "input_tokens": getattr(session, "input_tokens", 0),
            "output_tokens": getattr(session, "output_tokens", 0),
            "total_findings": getattr(session, "total_findings", 0),
            "total_tool_calls": getattr(session, "total_tool_calls", 0),
        },
    )

    return state