"""DBSpec parser utilities.

Utilities for parsing DBSpec files into database schema model objects.
"""

import re

from dbspec.errors import DBSpecParseError
from dbspec.models import Table


def _extract_fullmatch_groups(
    pattern: str, value: str, msg: str, *, flags: re.RegexFlag = re.NOFLAG
) -> tuple[str | None, ...]:
    """Extract fullmatch groups from a regex pattern.

    Given a regex pattern containing capturing groups, validate that the
    pattern matches the entire value. If so, return a tuple of the
    captures groups; otherwise, raise `DBSpecParseError`.

    Args:
        pattern: The regex pattern to match, containing the capturing
          groups to be extracted.
        value: The string to match against the pattern.
        msg: The error message to raise if the match fails.
        flags: Optional regex flags.

    Returns:
        A tuple containing the matched groups, with length equal to the
          number of capturing groups in the pattern.

    Raises:
        DBSpecParseError: If the provided value does not fully match the
          expected pattern.
    """
    match = re.fullmatch(pattern, value, flags=flags)
    if match is None:
        raise DBSpecParseError(msg)
    return match.groups()


def parse_table_declaration(declaration: str) -> Table:
    """Parse a table declaration into a `Table` object.

    Table declarations are expected to be of the form:

        TABLE <schema>.<table_name>

    For example:

        TABLE dbo.organisations

    The `TABLE` keyword is case-insensitive.
    """
    schema, name = _extract_fullmatch_groups(
        r"TABLE\s+([^.\s]+)\.([^.\s]+)",
        declaration.strip(),
        f"Invalid table declaration: {declaration!r}",
        flags=re.IGNORECASE,
    )
    return Table(schema=schema, name=name)
