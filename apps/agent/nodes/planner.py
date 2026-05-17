from __future__ import annotations

import json
import re
from typing import Any

from apps.agent.llm import LLMNotConfiguredError, invoke_text_with_usage
from apps.agent.prompts import PLANNER_PROMPT, SYSTEM_PROMPT
from apps.agent.state import ResearchAgentState
from apps.agent.tools.database_tools import emit_event, increment_token_usage
from apps.research.models import ResearchSession


IMPLEMENTATION_FALLBACKS = {
    "dependency": [
        "solve_dependencies",
        "get_dependant",
        "get_flat_dependant",
        "Dependant",
        "Depends",
        "dependency_overrides",
        "analyze_param",
        "request_params_to_args",
        "fastapi/dependencies",
    ],
    "authentication": [
        "authenticate",
        "permission",
        "token",
        "jwt",
        "oauth",
        "middleware",
    ],
    "routing": [
        "APIRoute",
        "APIRouter",
        "routing",
        "get_route_handler",
        "request_response",
    ],
}


def extract_json(text: str) -> dict[str, Any]:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)

    if not match:
        return {}

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}


def fallback_plan(question: str) -> dict[str, Any]:
    lower = question.lower()
    search_terms: list[str] = []

    for key, terms in IMPLEMENTATION_FALLBACKS.items():
        if key in lower:
            search_terms.extend(terms)

    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", question)

    for word in words:
        if word.lower() not in {
            "how",
            "does",
            "the",
            "and",
            "for",
            "with",
            "internally",
            "handle",
            "handles",
            "fastapi",
        }:
            search_terms.append(word)

    if not search_terms:
        search_terms = words[:8] or [question[:40]]

    unique_terms: list[str] = []
    seen = set()

    for term in search_terms:
        key = term.lower()

        if key in seen:
            continue

        seen.add(key)
        unique_terms.append(term)

    likely_paths = []

    if "dependency" in lower:
        likely_paths = [
            "fastapi/dependencies",
            "fastapi/params.py",
            "fastapi/routing.py",
        ]

    return {
        "search_terms": unique_terms[:12],
        "likely_paths": likely_paths,
        "source_first": True,
        "include_docs": False,
        "include_tests": False,
    }


def planner_node(state: ResearchAgentState) -> ResearchAgentState:
    session_id = state["session_id"]
    session = ResearchSession.objects.select_related("repository").get(id=session_id)

    emit_event(
        session_id=session_id,
        event_type="planning_started",
        title="Planning research",
        message="Creating source-first search strategy.",
    )

    options = dict(state.get("options", {}) or {})
    options["llm_provider"] = state.get("llm_provider") or session.llm_provider or options.get("llm_provider")
    options["model_name"] = state.get("model_name") or session.model_name or options.get("model_name")

    prompt = PLANNER_PROMPT.format(
        repository_name=session.repository.display_name,
        question=session.question,
    )

    try:
        result = invoke_text_with_usage(
            system_prompt=SYSTEM_PROMPT,
            human_prompt=prompt,
            options=options,
        )

        increment_token_usage(
            session_id=session_id,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
        )

        plan = extract_json(result.content)

    except LLMNotConfiguredError:
        plan = fallback_plan(session.question)

    except Exception as exc:
        emit_event(
            session_id=session_id,
            event_type="planning_warning",
            title="LLM planning failed",
            message=str(exc),
            payload={"fallback": True},
        )
        plan = fallback_plan(session.question)

    fallback = fallback_plan(session.question)

    search_terms = plan.get("search_terms") or fallback["search_terms"]

    # Always merge implementation fallbacks for internal questions.
    merged_terms = []
    for term in list(search_terms) + fallback["search_terms"]:
        if term and term not in merged_terms:
            merged_terms.append(term)

    state["search_terms"] = merged_terms[:12]
    state["likely_paths"] = plan.get("likely_paths") or fallback["likely_paths"]
    state["source_first"] = bool(plan.get("source_first", True))
    state["include_docs"] = bool(plan.get("include_docs", False))
    state["include_tests"] = bool(plan.get("include_tests", False))

    emit_event(
        session_id=session_id,
        event_type="planning_completed",
        title="Research plan ready",
        message="Source-first search plan prepared.",
        payload={
            "search_terms": state["search_terms"],
            "likely_paths": state["likely_paths"],
            "source_first": state["source_first"],
            "include_docs": state["include_docs"],
            "include_tests": state["include_tests"],
        },
    )

    return state