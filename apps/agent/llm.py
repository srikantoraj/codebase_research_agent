from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from langchain_core.messages import HumanMessage, SystemMessage


DEFAULT_PROVIDER = "openai"


class LLMNotConfiguredError(RuntimeError):
    pass


@dataclass
class LLMCallResult:
    content: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    provider: str = ""
    model_name: str = ""
    raw_response: Any = None


class LLMFactory:
    """
    Creates chat models from request options, Django settings, or environment.

    Default provider: OpenAI.
    Per-request override:
        options = {
            "llm_provider": "anthropic",
            "model_name": "claude-3-5-sonnet-latest"
        }
    """

    @classmethod
    def resolve_provider(cls, options: dict[str, Any] | None = None) -> str:
        options = options or {}

        provider = (
            options.get("llm_provider")
            or getattr(settings, "LLM_PROVIDER", None)
            or os.getenv("LLM_PROVIDER")
            or DEFAULT_PROVIDER
        )

        return str(provider).strip().lower()

    @classmethod
    def resolve_model_name(
        cls,
        provider: str,
        options: dict[str, Any] | None = None,
    ) -> str:
        options = options or {}

        if options.get("model_name"):
            return str(options["model_name"]).strip()

        if provider == "anthropic":
            return (
                getattr(settings, "ANTHROPIC_MODEL", None)
                or os.getenv("ANTHROPIC_MODEL")
                or "claude-3-5-sonnet-latest"
            )

        return (
            getattr(settings, "OPENAI_MODEL", None)
            or os.getenv("OPENAI_MODEL")
            or "gpt-4o-mini"
        )

    @classmethod
    def resolve_api_key(cls, provider: str) -> str:
        if provider == "anthropic":
            return (
                getattr(settings, "ANTHROPIC_API_KEY", "")
                or os.getenv("ANTHROPIC_API_KEY", "")
            )

        return (
            getattr(settings, "OPENAI_API_KEY", "")
            or os.getenv("OPENAI_API_KEY", "")
        )

    @classmethod
    def create(cls, options: dict[str, Any] | None = None):
        options = options or {}

        provider = cls.resolve_provider(options)
        model_name = cls.resolve_model_name(provider, options)
        temperature = float(options.get("temperature", 0.0))
        api_key = cls.resolve_api_key(provider)

        if provider == "anthropic":
            if not api_key:
                raise LLMNotConfiguredError("ANTHROPIC_API_KEY is missing.")

            os.environ["ANTHROPIC_API_KEY"] = api_key

            from langchain_anthropic import ChatAnthropic

            return ChatAnthropic(
                model=model_name,
                temperature=temperature,
                timeout=60,
                max_retries=2,
            )

        if not api_key:
            raise LLMNotConfiguredError("OPENAI_API_KEY is missing.")

        os.environ["OPENAI_API_KEY"] = api_key

        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            timeout=60,
            max_retries=2,
        )


def _content_to_text(content: Any) -> str:
    """
    LangChain message content can be string or list of structured blocks.
    This normalizes it into plain text.
    """

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        parts: list[str] = []

        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and item.get("text"):
                    parts.append(str(item["text"]))
                elif item.get("content"):
                    parts.append(str(item["content"]))
                else:
                    parts.append(str(item))
            else:
                parts.append(str(item))

        return "\n".join(parts)

    return str(content or "")


def extract_token_usage(response: Any) -> tuple[int, int, int]:
    """
    Works with LangChain OpenAI and Anthropic response metadata.

    Possible locations:
    - response.usage_metadata
    - response.response_metadata["token_usage"]
    - response.response_metadata["usage"]
    """

    usage = getattr(response, "usage_metadata", None) or {}
    metadata = getattr(response, "response_metadata", None) or {}

    token_usage = metadata.get("token_usage") or {}
    usage_obj = metadata.get("usage") or {}

    input_tokens = (
        usage.get("input_tokens")
        or usage.get("prompt_tokens")
        or token_usage.get("prompt_tokens")
        or token_usage.get("input_tokens")
        or usage_obj.get("input_tokens")
        or usage_obj.get("prompt_tokens")
        or 0
    )

    output_tokens = (
        usage.get("output_tokens")
        or usage.get("completion_tokens")
        or token_usage.get("completion_tokens")
        or token_usage.get("output_tokens")
        or usage_obj.get("output_tokens")
        or usage_obj.get("completion_tokens")
        or 0
    )

    total_tokens = (
        usage.get("total_tokens")
        or token_usage.get("total_tokens")
        or usage_obj.get("total_tokens")
        or int(input_tokens or 0) + int(output_tokens or 0)
    )

    return int(input_tokens or 0), int(output_tokens or 0), int(total_tokens or 0)


def invoke_text_with_usage(
    system_prompt: str,
    human_prompt: str,
    options: dict[str, Any] | None = None,
) -> LLMCallResult:
    options = options or {}

    provider = LLMFactory.resolve_provider(options)
    model_name = LLMFactory.resolve_model_name(provider, options)

    llm = LLMFactory.create(options)

    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt),
        ]
    )

    input_tokens, output_tokens, total_tokens = extract_token_usage(response)

    return LLMCallResult(
        content=_content_to_text(getattr(response, "content", "")),
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        provider=provider,
        model_name=model_name,
        raw_response=response,
    )


def invoke_text(
    system_prompt: str,
    human_prompt: str,
    options: dict[str, Any] | None = None,
) -> str:
    """
    Backward-compatible helper for old planner/research nodes.
    Use invoke_text_with_usage() where token tracking is required.
    """

    return invoke_text_with_usage(
        system_prompt=system_prompt,
        human_prompt=human_prompt,
        options=options,
    ).content