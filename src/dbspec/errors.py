"""DBSpec exception types."""


class DBSpecError(Exception):
    """Base class for all DBSpec exceptions."""


class DBSpecParseError(DBSpecError):
    """Raised when a DBSpec file cannot be parsed."""
