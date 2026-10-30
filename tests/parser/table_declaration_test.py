"""DBSpec table declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.parser import parse_table_declaration
from tests.utils import (
    EMPTY_DECLARATIONS,
    INVALID_IDENTIFIERS,
    VALID_IDENTIFIERS,
    WHITESPACE_SEPARATORS,
    parametrize_cases,
)

SCHEMA = "dbo"
TABLE = "organisations"


# ---------------------
# Valid format variants
# ---------------------
@parametrize_cases(
    "declaration",
    (f"TABLE {SCHEMA}.{TABLE}", "expected-format"),
    (f"table {SCHEMA}.{TABLE}", "lowercase-keyword"),
    (f"Table {SCHEMA}.{TABLE}", "mixed-case-keyword"),
    (f"    TABLE {SCHEMA}.{TABLE}    ", "outer-whitespace"),
    *(
        (f"TABLE{sep}{SCHEMA}.{TABLE}", f"separator_{case_id}")
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_format(declaration: str) -> None:
    """Parse a valid table declaration."""
    table = parse_table_declaration(declaration)
    table = table.identifier

    assert table.schema == SCHEMA
    assert table.name == TABLE


# ---------------------
# Invalid format variants
# ---------------------
@parametrize_cases(
    "declaration",
    *EMPTY_DECLARATIONS,
    ("TABLE", "keyword-only"),
    (f"{TABLE}", "schema-or-name-only"),
    (f"{SCHEMA}.{TABLE}", "missing-keyword"),
    (f"TABLE {TABLE}", "missing-schema-or-name"),
    (f"TABL {SCHEMA}.{TABLE}", "incorrect-keyword"),
    (f"TABLE .{TABLE}", "empty-schema"),
    (f"TABLE {SCHEMA}.", "empty-table-name"),
    (f"TABLE {SCHEMA} {TABLE}", "incorrect-separator-space"),
    (f"TABLE {SCHEMA}-{TABLE}", "incorrect-separator-punctuation"),
    (f"TABLE {SCHEMA} .{TABLE}", "space-before-separator"),
    (f"TABLE {SCHEMA}. {TABLE}", "space-after-separator"),
    (f"TABLE {SCHEMA}.{TABLE}.extra", "additional-name-part"),
)
def test_invalid_format(declaration: str) -> None:
    """Reject an invalid table declaration."""
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(declaration)


# -------------------------
# Valid identifier variants
# -------------------------
@parametrize_cases("identifier", *VALID_IDENTIFIERS)
def test_valid_identifier(identifier: str) -> None:
    """Parse a table declaration using a valid identifier."""
    table = parse_table_declaration(f"TABLE {identifier}.{TABLE}")
    table = table.identifier

    assert table.schema == identifier
    assert table.name == TABLE

    table = parse_table_declaration(f"TABLE {SCHEMA}.{identifier}")
    table = table.identifier

    assert table.schema == SCHEMA
    assert table.name == identifier


# ---------------------------
# Invalid identifier variants
# ---------------------------
@parametrize_cases("identifier", *INVALID_IDENTIFIERS)
def test_invalid_identifier(identifier: str) -> None:
    """Reject a table declaration using an invalid identifier."""
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(f"TABLE {identifier}.{TABLE}")
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(f"TABLE {SCHEMA}.{identifier}")
