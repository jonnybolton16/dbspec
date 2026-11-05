"""DBSpec table declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.parser import parse_table_declaration
from tests.utils import (
    EMPTY_DECLARATIONS,
    INVALID_IDENTIFIERS,
    SCHEMA,
    TABLE_NAME,
    VALID_IDENTIFIERS,
    VALID_SCHEMA_TABLE_FORMAT,
    WHITESPACE_SEPARATORS,
    parametrize_cases,
)


# ---------------------
# Valid format variants
# ---------------------
@parametrize_cases(
    "declaration",
    (f"TABLE {VALID_SCHEMA_TABLE_FORMAT}", "expected-format"),
    (f"table {VALID_SCHEMA_TABLE_FORMAT}", "lowercase-keyword"),
    (f"Table {VALID_SCHEMA_TABLE_FORMAT}", "mixed-case-keyword"),
    (f"    TABLE {VALID_SCHEMA_TABLE_FORMAT}    ", "outer-whitespace"),
    *(
        (f"TABLE{sep}{VALID_SCHEMA_TABLE_FORMAT}", f"separator_{case_id}")
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_format(declaration: str) -> None:
    """Parse a valid table declaration."""
    table = parse_table_declaration(declaration)
    table = table.identifier

    assert table.schema == SCHEMA
    assert table.name == TABLE_NAME


# ---------------------
# Invalid format variants
# ---------------------
@parametrize_cases(
    "declaration",
    *EMPTY_DECLARATIONS,
    ("TABLE", "keyword-only"),
    (f"{TABLE_NAME}", "schema-or-name-only"),
    (f"{VALID_SCHEMA_TABLE_FORMAT}", "missing-keyword"),
    (f"TABL {VALID_SCHEMA_TABLE_FORMAT}", "incorrect-keyword"),
    (f"TABLE {TABLE}", "missing-schema-or-name"),
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
    table = parse_table_declaration(f"TABLE {identifier}.{TABLE_NAME}")
    table = table.identifier

    assert table.schema == identifier
    assert table.name == TABLE_NAME

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
        parse_table_declaration(f"TABLE {identifier}.{TABLE_NAME}")
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(f"TABLE {SCHEMA}.{identifier}")
