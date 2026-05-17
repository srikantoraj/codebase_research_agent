class ApplicationError(Exception):
    """Base application exception for service-layer errors."""


class ValidationApplicationError(ApplicationError):
    """Raised when a service receives invalid input."""
