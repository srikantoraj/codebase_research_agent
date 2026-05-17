from __future__ import annotations

from pathlib import Path

from apps.agent.guards import BINARY_EXTENSIONS, IGNORED_DIRS, DEFAULT_MAX_FILE_CHARS


def is_ignored_path(path: Path) -> bool:
    return any(part in IGNORED_DIRS for part in path.parts)


def is_supported_source_file(path: Path) -> bool:
    if is_ignored_path(path):
        return False
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return False
    if not path.is_file():
        return False
    return True


def truncate_text(text: str, max_chars: int = DEFAULT_MAX_FILE_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[... truncated for context budget ...]"


def with_line_numbers(text: str, start_line: int = 1) -> str:
    lines = text.splitlines()
    return "\n".join(f"{idx + start_line:>5}: {line}" for idx, line in enumerate(lines))
