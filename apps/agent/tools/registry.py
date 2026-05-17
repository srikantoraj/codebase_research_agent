from __future__ import annotations

from apps.agent.tools.code_tools import list_files, read_around_match, read_file, search_code
from apps.agent.tools.database_tools import get_previous_findings, list_past_sessions, save_finding

TOOL_REGISTRY = {
    "list_files": list_files,
    "search_code": search_code,
    "read_file": read_file,
    "read_around_match": read_around_match,
    "save_finding": save_finding,
    "get_previous_findings": get_previous_findings,
    "list_past_sessions": list_past_sessions,
}
