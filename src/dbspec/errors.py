"""DBSpec exception types."""


class DBSpecError(Exception):
    """Base class for all DBSpec exceptions."""


class DBSpecModelError(DBSpecError):
    """Raised when a DBSpec model fails validation."""


class DBSpecParseError(DBSpecError):
    """Raised when a DBSpec file cannot be parsed."""
