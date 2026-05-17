from __future__ import annotations

import re
from typing import Any


def extract_function_name(line: str) -> str:
    patterns = [
        r"\bdef\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        r"\basync\s+def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        r"\bclass\s+([a-zA-Z_][a-zA-Z0-9_]*)\b",
        r"\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(",
        r"\bconst\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*=",
    ]
    for pattern in patterns:
        match = re.search(pattern, line)
        if match:
            return match.group(1)
    return ""


def normalize_reference(file_path: str, line_number: int | None = None, function_name: str = "") -> dict[str, Any]:
    return {
        "file_path": file_path,
        "line_start": line_number,
        "line_end": line_number,
        "function_name": function_name or "",
    }
