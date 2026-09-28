"""DBSpec table declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.parser import parse_table_declaration

SCHEMA = "dbo"
TABLE = "organisations"


@pytest.mark.parametrize(
    "declaration",
    [
        # expected format
        f"TABLE {SCHEMA}.{TABLE}",
        # outer whitespace
        f"    TABLE {SCHEMA}.{TABLE}    ",
        # inner whitespace
        f"TABLE    {SCHEMA}.{TABLE}",
        # tab whitespace
        f"TABLE\t{SCHEMA}.{TABLE}",
        # lowercase keyword
        f"table {SCHEMA}.{TABLE}",
        # mixed-case keyword
        f"Table {SCHEMA}.{TABLE}",
    ],
)
def test_valid(declaration: str) -> None:
    """Parse a valid table declaration."""
    table = parse_table_declaration(declaration)

    assert table.schema == SCHEMA
    assert table.name == TABLE


def test_valid_with_underscores() -> None:
    """Parse a valid table declaration with underscores in names."""
    table = parse_table_declaration(f"TABLE temp_{SCHEMA}.{TABLE}_v2")

    assert table.schema == "temp_" + SCHEMA
    assert table.name == TABLE + "_v2"


@pytest.mark.parametrize(
    "declaration",
    [
        # empty declaration
        "",
        # space only
        "    ",
        # other whitespace only
        "\t",
        # keyword only
        "TABLE",
        # schema or name only
        f"{TABLE}",
        # missing keyword
        f"{SCHEMA}.{TABLE}",
        # missing schema or name
        f"TABLE {TABLE}",
        # incorrect keyword
        f"TABL {SCHEMA}.{TABLE}",
        # empty schema
        f"TABLE .{TABLE}",
        # empty table name
        f"TABLE {SCHEMA}.",
        # incorrect schema/table separator (space)
        f"TABLE {SCHEMA} {TABLE}",
        # incorrect schema/table separator (punctuation)
        f"TABLE {SCHEMA}-{TABLE}",
        # space before separator
        f"TABLE {SCHEMA} .{TABLE}",
        # space after separator
        f"TABLE {SCHEMA}. {TABLE}",
        # additional name part
        f"TABLE {SCHEMA}.{TABLE}.extra",
    ],
)
def test_invalid(declaration: str) -> None:
    """Reject an invalid table declaration."""
    with pytest.raises(DBSpecParseError):
        parse_table_declaration(declaration)
