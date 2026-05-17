from pathlib import Path


def ensure_directory(path):
    """Create a directory if it does not exist and return it as Path."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def normalize_text(value):
    if value is None:
        return ""
    return str(value).strip()
