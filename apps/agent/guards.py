from __future__ import annotations

import os

DEFAULT_MAX_STEPS = int(os.getenv("AGENT_MAX_STEPS", "8"))
DEFAULT_MAX_FILES_TO_READ = int(os.getenv("AGENT_MAX_FILES_TO_READ", "8"))
DEFAULT_MAX_FILE_CHARS = int(os.getenv("AGENT_MAX_FILE_CHARS", "14000"))
MAX_SEARCH_RESULTS_PER_TERM = 12

ALLOWED_EXTENSIONS = {
    ".py", ".js", ".jsx", ".ts", ".tsx", ".go", ".java", ".rb", ".php",
    ".rs", ".c", ".cpp", ".h", ".hpp", ".cs", ".swift", ".kt", ".scala",
    ".md", ".rst", ".txt", ".toml", ".yaml", ".yml", ".json", ".ini",
}

IGNORED_DIRS = {
    ".git", ".hg", ".svn", "node_modules", "venv", ".venv", "env", ".env",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".next",
    "dist", "build", "coverage", ".idea", ".vscode", "site-packages",
}

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".pdf", ".zip", ".tar",
    ".gz", ".rar", ".7z", ".mp4", ".mov", ".mp3", ".wav", ".woff", ".woff2",
    ".ttf", ".eot", ".pyc", ".so", ".dylib", ".dll", ".exe",
}
