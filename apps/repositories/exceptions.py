class RepositoryError(Exception):
    """Base exception for repository service errors."""


class InvalidRepositoryURLError(RepositoryError):
    """Raised when a GitHub repository URL cannot be parsed or is unsupported."""


class InvalidLocalRepositoryPathError(RepositoryError):
    """Raised when a local repository path is missing or invalid."""


class RepositorySyncError(RepositoryError):
    """Raised when clone, pull, or repository inspection fails."""
