from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any


SOURCE_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".java",
    ".go",
    ".rs",
    ".php",
    ".rb",
    ".cs",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".swift",
    ".kt",
    ".sql",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".md",
}


ALWAYS_EXCLUDED_DIRS = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".next",
    ".turbo",
    "coverage",
}


SOURCE_FIRST_EXCLUDED_DIRS = {
    "docs",
    "tests",
    "test",
    "examples",
    "example",
    "scripts",
}


SOURCE_PRIORITY_DIRS = {
    "fastapi",
    "src",
    "app",
    "apps",
    "core",
    "lib",
    "package",
    "packages",
}


IMPLEMENTATION_HINTS = {
    "solve_dependencies",
    "get_dependant",
    "get_flat_dependant",
    "Dependant",
    "Depends",
    "dependency_overrides",
    "analyze_param",
    "request_params_to_args",
}


def normalize_query(query: str) -> str:
    return (query or "").strip()


def is_supported_source_file(path: Path) -> bool:
    if path.suffix in SOURCE_EXTENSIONS:
        return True

    if path.name in {"Dockerfile", "Makefile", "README", "LICENSE"}:
        return True

    return False


def should_skip_path(
    path: Path,
    root: Path,
    source_first: bool = True,
    include_docs: bool = False,
    include_tests: bool = False,
) -> bool:
    try:
        rel_parts = path.relative_to(root).parts
    except ValueError:
        rel_parts = path.parts

    parts = set(rel_parts)

    if parts.intersection(ALWAYS_EXCLUDED_DIRS):
        return True

    if source_first:
        if not include_docs and "docs" in parts:
            return True

        if not include_tests and parts.intersection({"tests", "test"}):
            return True

        if parts.intersection({"examples", "example"}):
            return True

    return False


def score_match(file_path: str, line: str, query: str, function_name: str = "") -> float:
    score = 0.5

    lower_path = file_path.lower()
    lower_line = line.lower()
    lower_query = query.lower()

    if lower_query in lower_line:
        score += 0.25

    for part in lower_path.split("/"):
        if part in SOURCE_PRIORITY_DIRS:
            score += 0.25

    if file_path.endswith(".py"):
        score += 0.2

    if function_name:
        score += 0.15

    if any(hint.lower() in lower_line or hint.lower() in lower_path for hint in IMPLEMENTATION_HINTS):
        score += 0.35

    if lower_path.startswith("docs/"):
        score -= 0.35

    if lower_path.startswith("tests/") or "/tests/" in lower_path:
        score -= 0.2

    if lower_path.endswith(".md"):
        score -= 0.2

    return round(max(0.0, min(score, 1.0)), 3)


def detect_function_name(line: str, current_function: str = "") -> str:
    stripped = line.strip()

    match = re.match(r"^(async\s+def|def)\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", stripped)
    if match:
        return match.group(2)

    class_match = re.match(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\s*[\(:]", stripped)
    if class_match:
        return class_match.group(1)

    return current_function


def list_files(
    repo_path: str,
    max_results: int = 500,
    source_first: bool = True,
    include_docs: bool = False,
    include_tests: bool = False,
) -> dict[str, Any]:
    root = Path(repo_path)

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    files: list[str] = []

    for current_root, dirs, filenames in os.walk(root):
        current_path = Path(current_root)

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in ALWAYS_EXCLUDED_DIRS
        ]

        for filename in filenames:
            path = current_path / filename

            if should_skip_path(
                path=path,
                root=root,
                source_first=source_first,
                include_docs=include_docs,
                include_tests=include_tests,
            ):
                continue

            if not is_supported_source_file(path):
                continue

            rel_path = str(path.relative_to(root))
            files.append(rel_path)

            if len(files) >= max_results:
                return {"count": len(files), "files": files}

    return {"count": len(files), "files": files}


def search_code(
    repo_path: str,
    query: str,
    max_results: int = 12,
    max_file_bytes: int = 800000,
    source_first: bool = True,
    include_docs: bool = False,
    include_tests: bool = False,
    likely_paths: list[str] | None = None,
) -> dict[str, Any]:
    query = normalize_query(query)
    root = Path(repo_path)

    if not root.exists() or not root.is_dir():
        raise ValueError(f"Repository path does not exist: {repo_path}")

    likely_paths = likely_paths or []
    query_lower = query.lower()
    results: list[dict[str, Any]] = []

    for current_root, dirs, filenames in os.walk(root):
        current_path = Path(current_root)

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in ALWAYS_EXCLUDED_DIRS
        ]

        for filename in filenames:
            path = current_path / filename

            if should_skip_path(
                path=path,
                root=root,
                source_first=source_first,
                include_docs=include_docs,
                include_tests=include_tests,
            ):
                continue

            if not is_supported_source_file(path):
                continue

            try:
                if path.stat().st_size > max_file_bytes:
                    continue

                rel_path = str(path.relative_to(root))

                with path.open("r", encoding="utf-8", errors="ignore") as handle:
                    current_function = ""

                    for line_number, line in enumerate(handle, start=1):
                        current_function = detect_function_name(line, current_function)
                        line_lower = line.lower()

                        matched = False

                        if query_lower and query_lower in line_lower:
                            matched = True

                        if query_lower and query_lower in rel_path.lower():
                            matched = True

                        for likely_path in likely_paths:
                            if likely_path and likely_path.lower() in rel_path.lower():
                                matched = True

                        if not matched:
                            continue

                        results.append(
                            {
                                "file_path": rel_path,
                                "line_number": line_number,
                                "line": line.strip(),
                                "function_name": current_function,
                                "score": score_match(
                                    file_path=rel_path,
                                    line=line,
                                    query=query,
                                    function_name=current_function,
                                ),
                            }
                        )

            except OSError:
                continue

    results = sorted(
        results,
        key=lambda item: item.get("score", 0),
        reverse=True,
    )[:max_results]

    return {
        "query": query,
        "count": len(results),
        "results": results,
    }


def read_file(
    repo_path: str,
    file_path: str,
    start_line: int | None = None,
    end_line: int | None = None,
    max_chars: int = 16000,
) -> dict[str, Any]:
    root = Path(repo_path)
    path = (root / file_path).resolve()

    if not str(path).startswith(str(root.resolve())):
        raise ValueError("Invalid file path outside repository.")

    if not path.exists() or not path.is_file():
        raise ValueError(f"File does not exist: {file_path}")

    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()

    total_lines = len(lines)
    start = max(1, int(start_line or 1))
    end = min(total_lines, int(end_line or total_lines))

    selected = lines[start - 1:end]

    content_lines = [
        f"{line_number:>5}: {line}"
        for line_number, line in enumerate(selected, start=start)
    ]

    content = "\n".join(content_lines)

    if len(content) > max_chars:
        content = content[:max_chars] + "\n... truncated ..."

    return {
        "file_path": file_path,
        "start_line": start,
        "end_line": end,
        "total_lines": total_lines,
        "content": content,
    }


def read_around_match(
    repo_path: str,
    match: dict[str, Any],
    before: int = 35,
    after: int = 90,
    max_chars: int = 16000,
) -> dict[str, Any]:
    file_path = match.get("file_path", "")
    line_number = int(match.get("line_number") or 1)

    start_line = max(1, line_number - before)
    end_line = line_number + after

    return read_file(
        repo_path=repo_path,
        file_path=file_path,
        start_line=start_line,
        end_line=end_line,
        max_chars=max_chars,
    )