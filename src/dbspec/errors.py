"""DBSpec exception types."""


class DBSpecError(Exception):
    """Base class for all DBSpec exceptions."""


class DBSpecFileError(DBSpecError):
    """Raised when a DBSpec file cannot be processed."""


class DBSpecModelError(DBSpecError):
    """Raised when a DBSpec model fails validation."""


class DBSpecParseError(DBSpecError):
    """Raised when the contents of a DBSpec file cannot be parsed."""
