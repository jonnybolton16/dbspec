"""DBSpec table declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.parser import parse_table_declaration
from tests.utils import case_params

SCHEMA = "dbo"
TABLE = "organisations"

VALID_DECLARATIONS = [
    (f"TABLE {SCHEMA}.{TABLE}", "expected-format"),
    (f"    TABLE {SCHEMA}.{TABLE}    ", "outer-whitespace"),
    (f"TABLE    {SCHEMA}.{TABLE}", "inner-whitespace"),
    (f"TABLE\t{SCHEMA}.{TABLE}", "tab-whitespace"),
    (f"table {SCHEMA}.{TABLE}", "lowercase-keyword"),
    (f"Table {SCHEMA}.{TABLE}", "mixed-case-keyword"),
]


@pytest.mark.parametrize("declaration", case_params(VALID_DECLARATIONS))
def test_valid(declaration: str) -> None:
    """Parse a valid table declaration."""
    table = parse_table_declaration(declaration)
    table = table.identifier

    assert table.schema == SCHEMA
    assert table.name == TABLE


def test_valid_with_underscores() -> None:
    """Parse a valid table declaration with underscores in names."""
    table = parse_table_declaration(f"TABLE temp_{SCHEMA}.{TABLE}_v2")
    table = table.identifier

    assert table.schema == "temp_" + SCHEMA
    assert table.name == TABLE + "_v2"


INVALID_DECLARATIONS = [
    ("", "empty-declaration"),
    ("    ", "space-only"),
    ("\t", "other-whitespace-only"),
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
]


@pytest.mark.parametrize("declaration", case_params(INVALID_DECLARATIONS))
def test_invalid(declaration: str) -> None:
    """Reject an invalid table declaration."""
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(declaration)
