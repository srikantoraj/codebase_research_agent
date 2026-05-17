from __future__ import annotations

import time
from typing import Any, Callable

from apps.research.enums import FindingSource, ToolCallStatus, ToolCallType
from apps.research.models import AgentEvent, Finding, ResearchSession, ToolCallLog

try:
    from apps.realtime.services import RealtimeEventPublisher
except Exception:  # pragma: no cover
    RealtimeEventPublisher = None


def model_has_field(model, field_name: str) -> bool:
    return any(field.name == field_name for field in model._meta.fields)


def set_model_value(instance, field_name: str, value: Any) -> None:
    if model_has_field(instance.__class__, field_name):
        setattr(instance, field_name, value)


def get_session(session_id: str) -> ResearchSession:
    return ResearchSession.objects.select_related("repository").get(id=session_id)


def safe_enum_value(enum_class: Any, name: str, fallback: str) -> Any:
    return getattr(enum_class, name, fallback)


def infer_tool_type(tool_name: str) -> str:
    name = (tool_name or "").lower()

    if name in {
        "search_code",
        "read_file",
        "read_around_match",
        "list_files",
        "get_file_summary",
    }:
        return ToolCallType.CODE

    if name in {
        "get_previous_findings",
        "list_past_sessions",
        "save_finding",
        "load_context",
    }:
        return ToolCallType.DATABASE

    if "llm" in name or "answer" in name or "plan" in name:
        return safe_enum_value(ToolCallType, "LLM", "llm")

    return safe_enum_value(ToolCallType, "SYSTEM", "system")


def next_step(session: ResearchSession) -> int:
    if model_has_field(ResearchSession, "current_step"):
        session.current_step = (session.current_step or 0) + 1
        session.save(update_fields=["current_step", "updated_at"])
        return session.current_step

    return 0


def increment_token_usage(
    session_id: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> None:
    session = get_session(session_id)

    update_fields: list[str] = []

    if model_has_field(ResearchSession, "input_tokens"):
        session.input_tokens = (session.input_tokens or 0) + int(input_tokens or 0)
        update_fields.append("input_tokens")

    if model_has_field(ResearchSession, "output_tokens"):
        session.output_tokens = (session.output_tokens or 0) + int(output_tokens or 0)
        update_fields.append("output_tokens")

    if update_fields:
        update_fields.append("updated_at")
        session.save(update_fields=update_fields)


def emit_event(
    session_id: str,
    event_type: str,
    title: str,
    message: str = "",
    payload: dict[str, Any] | None = None,
    step_number: int | None = None,
) -> dict[str, Any]:
    """
    Persist an agent timeline event.

    Important:
    AgentEvent has ForeignKey `session`, so we attach the session object.
    Do not create it with filtered `session_id`.
    """

    session = get_session(session_id)
    payload = payload or {}

    if step_number is None:
        step_number = next_step(session)

    event = AgentEvent.objects.create(
        session=session,
        event_type=event_type,
        title=title,
        message=message or "",
        payload=payload,
        step_number=step_number or 0,
        is_public=True,
    )

    event_data = {
        "id": str(event.id),
        "session_id": str(session.id),
        "event_type": event.event_type,
        "title": event.title,
        "message": event.message,
        "payload": event.payload,
        "step_number": event.step_number,
        "created_at": event.created_at.isoformat(),
    }

    if RealtimeEventPublisher is not None:
        try:
            RealtimeEventPublisher.publish(session.id, event_data)
        except Exception:
            # Realtime should never break the agent.
            pass

    return event_data


def log_tool_call(
    session_id: str,
    tool_name: str,
    input_payload: dict[str, Any],
    output_payload: dict[str, Any] | None = None,
    success: bool = True,
    error_message: str = "",
    duration_ms: int = 0,
    step_number: int | None = None,
) -> None:
    """
    Persist a tool call.

    ToolCallLog requires both:
    - session
    - repository
    """

    session = get_session(session_id)

    if step_number is None:
        step_number = next_step(session)

    ToolCallLog.objects.create(
        session=session,
        repository=session.repository,
        tool_name=tool_name,
        tool_type=infer_tool_type(tool_name),
        status=ToolCallStatus.SUCCEEDED if success else ToolCallStatus.FAILED,
        step_number=step_number or 0,
        input_payload=input_payload or {},
        output_payload=output_payload or {},
        error_message=error_message or "",
        duration_ms=duration_ms or 0,
    )


def execute_logged_tool(
    session_id: str,
    tool_name: str,
    input_payload: dict[str, Any],
    func: Callable[..., dict[str, Any]],
    step_number: int | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()

    output: dict[str, Any] = {}
    success = True
    error_message = ""

    try:
        output = func(**(input_payload or {}))
        return output

    except Exception as exc:
        success = False
        error_message = str(exc)
        output = {"error": error_message}
        raise

    finally:
        duration_ms = int((time.perf_counter() - started) * 1000)

        log_tool_call(
            session_id=session_id,
            tool_name=tool_name,
            input_payload=input_payload or {},
            output_payload=output,
            success=success,
            error_message=error_message,
            duration_ms=duration_ms,
            step_number=step_number,
        )


def save_finding(
    session_id: str,
    file_path: str,
    note: str,
    function_name: str = "",
    line_start: int | None = None,
    line_end: int | None = None,
    confidence: float = 0.8,
    evidence_snippet: str = "",
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    session = get_session(session_id)

    finding = Finding.objects.create(
        session=session,
        repository=session.repository,
        source=FindingSource.AGENT,
        file_path=file_path,
        symbol_name=function_name or "",
        symbol_type="function" if function_name else "",
        line_start=line_start,
        line_end=line_end,
        note=note or "",
        evidence_snippet=evidence_snippet or "",
        confidence=confidence or 0.0,
        metadata=metadata or {},
    )

    emit_event(
        session_id=session_id,
        event_type="finding_saved",
        title="Finding saved",
        message=(note or "")[:300],
        payload=finding.reference,
    )

    return {
        "id": str(finding.id),
        "file_path": finding.file_path,
        "function_name": finding.symbol_name,
        "line_start": finding.line_start,
        "line_end": finding.line_end,
        "note": finding.note,
        "evidence_snippet": finding.evidence_snippet,
        "confidence": finding.confidence,
        "reference": finding.reference,
    }


def get_previous_findings(
    repository_id: str,
    limit: int = 15,
) -> list[dict[str, Any]]:
    qs = Finding.objects.filter(repository_id=repository_id).order_by("-created_at")[
        :limit
    ]

    results: list[dict[str, Any]] = []

    for item in qs:
        symbol_name = getattr(item, "symbol_name", "") or ""

        results.append(
            {
                "file_path": getattr(item, "file_path", ""),
                "function_name": symbol_name,
                "symbol_name": symbol_name,
                "symbol_type": getattr(item, "symbol_type", ""),
                "line_start": getattr(item, "line_start", None),
                "line_end": getattr(item, "line_end", None),
                "note": getattr(item, "note", ""),
                "evidence_snippet": getattr(item, "evidence_snippet", ""),
                "confidence": getattr(item, "confidence", None),
            }
        )

    return results


def list_past_sessions(
    repository_id: str,
    limit: int = 8,
) -> list[dict[str, Any]]:
    qs = ResearchSession.objects.filter(repository_id=repository_id).order_by(
        "-created_at"
    )[:limit]

    return [
        {
            "id": str(item.id),
            "question": item.question,
            "status": getattr(item, "status", ""),
            "created_at": (
                item.created_at.isoformat()
                if getattr(item, "created_at", None)
                else None
            ),
        }
        for item in qs
    ]