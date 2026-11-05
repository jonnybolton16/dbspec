"""DBSpec key declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.models import ForeignKey, PrimaryKey, UniqueKey
from dbspec.parser import parse_key_declaration
from tests.utils import (
    EMPTY_DECLARATIONS,
    INVALID_IDENTIFIERS,
    INVALID_SCHEMA_TABLE_FORMATS,
    VALID_IDENTIFIERS,
    WHITESPACE_SEPARATORS,
    parametrize_cases,
)

VALID_IDENTIFIER_LIST = [identifier for identifier, _ in VALID_IDENTIFIERS]

# ---------------------
# Error message regexes
# ---------------------
MSG_EMPTY = "Key declaration cannot be empty"
MSG_INVALID_KEY = (
    "Key declaration must contain exactly one occurrence of "
    "PRIMARY KEY, UNIQUE, or FOREIGN KEY"
)
MSG_KEY_NOT_AT_START = (
    "Key declaration must start with PRIMARY KEY, UNIQUE, or FOREIGN KEY"
)
MSG_PK_COLUMN_LIST = "Invalid PRIMARY KEY <column_list>"
MSG_UQ_COLUMN_LIST = "Invalid UNIQUE <column_list>"
MSG_FK_COLUMN_LIST = "Invalid FOREIGN KEY <column_list>"
MSG_REF_COUNT = (
    "Foreign key declaration must contain exactly one REFERENCES keyword"
)
MSG_REF_TARGET = "Invalid REFERENCES target"
MSG_REF_COLUMN_LIST = "Invalid REFERENCES <column_list>"
MSG_FK_MULTIPLE_TRIGGERS = (
    r"Foreign key declaration cannot contain "
    "multiple ON (DELETE|UPDATE) clauses"
)
MSG_FK_ACTION = r"Invalid ON (DELETE|UPDATE) action"


# -------------------------
# Rejection helper function
# -------------------------
def reject(declaration: str, message: str) -> None:
    """Reject a key declaration with the expected error message."""
    with pytest.raises(DBSpecParseError, match=message):
        parse_key_declaration(declaration)


# ----------------------------------
# Empty/whitespace-only declarations
# ----------------------------------
@parametrize_cases("declaration", *EMPTY_DECLARATIONS)
def test_invalid_empty_declaration(declaration: str) -> None:
    """Reject an empty/whitespace-only key declaration."""
    reject(declaration, MSG_EMPTY)


# --------------------------
# Missing/multiple key types
# --------------------------
### no valid key type ###
@parametrize_cases(
    "declaration",
    ("id", "no-key-type"),
    ("KEY id", "key-only"),
    ("PRIMARY id", "pk-missing-key"),
    ("FOREIGN id", "fk-missing-key"),
    # "unique" with "key" skipped; raises wrong error
    ("RIMARY KEY id", "pk-spelling"),
    ("UNIQUIE id", "uq-spelling"),
    ("FORIEGN KEY id", "fk-spelling"),
    ("id REFERENCES dbo.users(id)", "references-missing-fk"),
)
def test_invalid_missing_key_type(declaration: str) -> None:
    """Reject a key declaration with a missing key type."""
    reject(declaration, MSG_INVALID_KEY)


### multiple key types ###
@parametrize_cases(
    "declaration",
    ("PRIMARY KEY id PRIMARY KEY code", "pk-pk"),
    ("PRIMARY KEY id UNIQUE code", "pk-uq"),
    ("PRIMARY KEY id FOREIGN KEY code REFERENCES dbo.users(code)", "pk-fk"),
    ("UNIQUE id UNIQUE code", "uq-uq"),
    ("UNIQUE id FOREIGN KEY code REFERENCES dbo.users(code)", "uq-fk"),
    (
        "FOREIGN KEY id REFERENCES s.t(c) FOREIGN KEY code REFERENCES s.t(c)",
        "fk-fk",
    ),
)
def test_invalid_multiple_key_types(declaration: str) -> None:
    """Reject a key declaration with multiple key types."""
    reject(declaration, MSG_INVALID_KEY)


# ---------------------
# Key type not at start
# ---------------------
@parametrize_cases(
    "declaration",
    ("id INT PRIMARY KEY", "pk"),
    ("id INT UNIQUE", "uq"),
    ("id INT FOREIGN KEY REFERENCES dbo.users(id)", "fk"),
)
def test_invalid_key_not_at_start(declaration: str) -> None:
    """Reject a key declaration with the key type not at the start."""
    reject(declaration, MSG_KEY_NOT_AT_START)


# ------------
# Primary keys
# ------------
### keyword variants ###
@parametrize_cases(
    "keyword",
    ("PRIMARY KEY", "upper"),
    ("primary key", "lower"),
    ("Primary Key", "mixed"),
    *(
        (f"PRIMARY{sep}KEY", f"separator_{case_id}")
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_pk_keyword_variant(keyword: str) -> None:
    """Parse a primary key declaration with a varying keyword format."""
    key = parse_key_declaration(f"{keyword} id")

    assert isinstance(key, PrimaryKey)
    assert key.columns == ["id"]


### whitespace between keyword and column list ###
@parametrize_cases("space", *WHITESPACE_SEPARATORS)
def test_valid_pk_keyword_whitespace(space: str) -> None:
    """Parse a primary key with varying whitespace after the keyword."""
    key = parse_key_declaration(f"PRIMARY KEY{space}id")

    assert isinstance(key, PrimaryKey)
    assert key.columns == ["id"]


### valid identifiers, with/without brackets ###
@parametrize_cases(
    ("left", "right"), (("(", ")"), "brackets"), ((" ", ""), "bare")
)
@parametrize_cases("column", *VALID_IDENTIFIERS)
def test_valid_pk_single(left: str, right: str, column: str) -> None:
    """Parse a valid one-column key, with or without brackets."""
    key = parse_key_declaration(f"PRIMARY KEY{left}{column}{right}")

    assert isinstance(key, PrimaryKey)
    assert key.columns == [column]


### valid multi-column declarations, with/without brackets ###
@parametrize_cases(
    ("left", "right"), (("(", ")"), "brackets"), ((" ", ""), "bare")
)
@parametrize_cases("space", *WHITESPACE_SEPARATORS)
def test_valid_pk_multi(left: str, right: str, space: str) -> None:
    """Parse a valid multi-column primary key.

    Include optional brackets around the column list, and whitespace
    around the commas.
    """
    for sep in (",", f"{space},", f",{space}"):
        key = parse_key_declaration(
            f"PRIMARY KEY{left}{sep.join(VALID_IDENTIFIER_LIST)}{right}"
        )

        assert isinstance(key, PrimaryKey)
        assert key.columns == VALID_IDENTIFIER_LIST


### column name contains key-type ###
@parametrize_cases(
    "column",
    # bracketed key-type-like column names
    ("[primary key]", "pk"),
    ("[unique]", "uq"),
    ("[foreign key]", "fk"),
    # non-key-declaration keywords as column names
    ("table", "table"),
    ("null", "null"),
    ("identity", "identity"),
    ("default", "default"),
)
def test_valid_pk_key_type_like_name(column: str) -> None:
    """Parse a key-type-like column name."""
    key = parse_key_declaration(f"PRIMARY KEY {column}")

    assert isinstance(key, PrimaryKey)
    assert key.columns == [column]


### valid whitespace around brackets ###
@parametrize_cases("space", *WHITESPACE_SEPARATORS)
def test_valid_pk_bracket_whitespace(space: str) -> None:
    """Parse a primary key using whitespace alongside brackets."""
    for column in (
        f"{space}(id)",
        f"({space}id)",
        f"(id{space})",
        f"(id){space}",
    ):
        key = parse_key_declaration(f"PRIMARY KEY {column}")

        assert isinstance(key, PrimaryKey)
        assert key.columns == ["id"]


### invalid identifiers ###
@parametrize_cases("column", *INVALID_IDENTIFIERS)
def test_invalid_pk_single(column: str) -> None:
    """Reject a one-column primary key using an invalid identifier."""
    reject(f"PRIMARY KEY {column}", MSG_PK_COLUMN_LIST)


@parametrize_cases(
    "index",
    *((i, case_id) for i, (_, case_id) in enumerate(INVALID_IDENTIFIERS)),
)
def test_invalid_pk_multi(index: int) -> None:
    """Reject a multi-column primary key using an invalid identifier."""
    columns = list(reversed(VALID_IDENTIFIER_LIST))
    columns[index] = INVALID_IDENTIFIERS[index][0]

    reject(f"PRIMARY KEY ({', '.join(columns)})", MSG_PK_COLUMN_LIST)


### malformed column lists ###
@parametrize_cases(
    "column_list",
    ("", "blank"),
    ("()", "empty-brackets"),
    (",code", "leading-comma"),
    ("id,", "trailing-comma"),
    ("id,,code", "double-comma"),
    ("id, ,code", "empty-column"),
    ("(id,code", "missing-closing-bracket"),
    ("id,code)", "missing-opening-bracket"),
    ("((id,code))", "double-brackets"),
    ("(id,code) extra", "extra-text-after-brackets"),
)
def test_invalid_pk_malformed(column_list: str) -> None:
    """Reject a primary key with a malformed column list."""
    reject(f"PRIMARY KEY {column_list}", MSG_PK_COLUMN_LIST)


# -----------
# Unique keys
# -----------
### keyword variants ###
@parametrize_cases(
    "keyword",
    ("UNIQUE", "upper"),
    ("unique", "lower"),
    ("Unique", "mixed"),
)
def test_valid_uq_keyword_variant(keyword: str) -> None:
    """Parse a unique key declaration with a varying keyword format."""
    key = parse_key_declaration(f"{keyword} id")

    assert isinstance(key, UniqueKey)
    assert key.columns == ["id"]


### KEY keyword passed ###
def test_invalid_uq_key() -> None:
    """Reject a unique key using the KEY keyword."""
    reject("UNIQUE KEY id", MSG_UQ_COLUMN_LIST)


### check some unique keys without duplicating thorough PK testing ###
def test_valid_uq_single() -> None:
    """Parse a valid one-column unique key."""
    key = parse_key_declaration("UNIQUE [column name]")

    assert isinstance(key, UniqueKey)
    assert key.columns == ["[column name]"]


def test_valid_uq_multi() -> None:
    """Parse a valid multi-column unique key."""
    key = parse_key_declaration("UNIQUE (id, [column name], code)")

    assert isinstance(key, UniqueKey)
    assert key.columns == ["id", "[column name]", "code"]


def test_invalid_uq_malformed() -> None:
    """Reject a unique key with a malformed column list."""
    reject("UNIQUE ,code", MSG_UQ_COLUMN_LIST)


# ------------
# Foreign keys
# ------------
### keyword variants ###
@parametrize_cases(
    "keyword",
    ("FOREIGN KEY", "upper"),
    ("foreign key", "lower"),
    ("Foreign Key", "mixed"),
    *(
        (f"FOREIGN{sep}KEY", f"separator_{case_id}")
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_fk_keyword_variant(keyword: str) -> None:
    """Parse a foreign key declaration with a varying keyword format."""
    key = parse_key_declaration(f"{keyword} id REFERENCES dbo.users(id)")

    assert isinstance(key, ForeignKey)
    assert key.columns == ["id"]


@parametrize_cases(
    "keyword",
    ("REFERENCES", "upper"),
    ("references", "lower"),
    ("References", "mixed"),
)
@parametrize_cases("space", *WHITESPACE_SEPARATORS)
def test_valid_fk_references_variant(keyword: str, space: str) -> None:
    """Parse a foreign key with a varying REFERENCES keyword format."""
    key = parse_key_declaration(
        f"FOREIGN KEY id{space}{keyword}{space}dbo.users(id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.columns == ["id"]


### invalid REFERENCES counts ###
@parametrize_cases(
    "declaration",
    ("FOREIGN KEY id dbo.users(id)", "missing"),
    (
        "FOREIGN KEY id REFERENCES dbo.users(id) REFERENCES dbo.other(id)",
        "repeated",
    ),
)
def test_invalid_fk_references_count(declaration: str) -> None:
    """Reject a foreign key without exactly one REFERENCES keyword."""
    reject(declaration, MSG_REF_COUNT)


### bracketed REFERENCES keyword ###
def test_valid_fk_bracketed_references() -> None:
    """Parse a bracketed REFERENCES column name."""
    key = parse_key_declaration(
        "FOREIGN KEY [references] REFERENCES dbo.users(id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.columns == ["[references]"]


def test_invalid_fk_bracketed_references() -> None:
    """Reject a bracketed REFERENCES keyword."""
    reject("FOREIGN KEY [REFERENCES] dbo.users(id)", MSG_REF_COUNT)


### check some FK column lists ###
def test_valid_fk_single() -> None:
    """Parse a valid one-column foreign key."""
    key = parse_key_declaration("FOREIGN KEY(id)REFERENCES dbo.users(id)")

    assert isinstance(key, ForeignKey)
    assert key.columns == ["id"]


def test_valid_fk_multi() -> None:
    """Parse a valid multi-column foreign key."""
    key = parse_key_declaration(
        "FOREIGN KEY tenant_id, user_id REFERENCES dbo.users(tenant_id, id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.columns == ["tenant_id", "user_id"]


@parametrize_cases(
    "column_list",
    ("", "blank"),
    ("id,", "trailing-comma"),
)
def test_invalid_fk_malformed(column_list: str) -> None:
    """Reject a foreign key with a malformed column list."""
    reject(
        f"FOREIGN KEY {column_list}REFERENCES dbo.users(id)",
        MSG_FK_COLUMN_LIST,
    )


### REFERENCES target ###
@parametrize_cases("space", *WHITESPACE_SEPARATORS)
def test_valid_fk_references_target_whitespace(space: str) -> None:
    """Parse a referenced schema.table using varying whitespace."""
    key = parse_key_declaration(
        f"FOREIGN KEY id REFERENCES{space}dbo.users(id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.referenced_table.schema == "dbo"
    assert key.referenced_table.name == "users"


@parametrize_cases("identifier", *VALID_IDENTIFIERS)
def test_valid_fk_references_target_identifier(identifier: str) -> None:
    """Parse a referenced schema.table using a valid identifier."""
    key = parse_key_declaration(
        f"FOREIGN KEY id REFERENCES {identifier}.users(id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.referenced_table.schema == identifier
    assert key.referenced_table.name == "users"

    key = parse_key_declaration(
        f"FOREIGN KEY id REFERENCES dbo.{identifier}(id)"
    )

    assert isinstance(key, ForeignKey)
    assert key.referenced_table.schema == "dbo"
    assert key.referenced_table.name == identifier


@parametrize_cases("identifier", *INVALID_IDENTIFIERS)
def test_invalid_fk_references_target_identifier(
    identifier: str,
) -> None:
    """Reject a referenced schema.table using an invalid identifier."""
    reject(
        f"FOREIGN KEY id REFERENCES {identifier}.users(id)",
        MSG_REF_TARGET,
    )

    reject(
        f"FOREIGN KEY id REFERENCES dbo.{identifier}(id)",
        # "aB '5~@]]#)" gives column_list error, 'aB' is parsed as table
        MSG_REF_TARGET if identifier != "aB '5~@]]#)" else MSG_REF_COLUMN_LIST,
    )


@parametrize_cases(
    "fmt",
    ("", "blank"),
    *INVALID_SCHEMA_TABLE_FORMATS,
)
def test_invalid_fk_references_target_format(fmt: str) -> None:
    """Reject a referenced schema.table with using an invalid format."""
    reject(f"FOREIGN KEY id REFERENCES {fmt}(id)", MSG_REF_TARGET)


def test_invalid_fk_references_missing_target() -> None:
    """Reject a foreign key with nothing after REFERENCES."""
    reject("FOREIGN KEY id REFERENCES", MSG_REF_TARGET)


### REFERENCES column list ###
@parametrize_cases(
    ("left", "right"),
    (("(", ")"), "brackets"),
    ((" ", ""), "bare"),
    ((" (", ")"), "bracket-with-space"),
)
def test_valid_fk_references_column_brackets(left: str, right: str) -> None:
    """Parse a varying separator between REFERENCES table and column."""
    key = parse_key_declaration(
        f"FOREIGN KEY id REFERENCES dbo.users{left}ref_id{right}"
    )

    assert isinstance(key, ForeignKey)
    assert key.columns == ["id"]
    assert key.referenced_columns == ["ref_id"]

    key = parse_key_declaration(
        f"FOREIGN KEY a, b REFERENCES dbo.users{left}c, d{right}"
    )

    assert isinstance(key, ForeignKey)
    assert key.columns == ["a", "b"]
    assert key.referenced_columns == ["c", "d"]


@parametrize_cases(
    "column_list",
    ("", "blank"),
    ("id", "no-separator"),
    (" (id,code", "missing-closing-bracket"),
    (" (id,,code)", "double-comma"),
)
def test_invalid_fk_references_malformed(column_list: str) -> None:
    """Reject a foreign key with a malformed REFERENCES column list."""
    reject(
        f"FOREIGN KEY id REFERENCES dbo.users{column_list}",
        MSG_REF_COLUMN_LIST,
    )


### referential actions ###
@parametrize_cases(
    "action",
    ("CASCADE", "cascade"),
    ("NO ACTION", "no-action"),
    ("SET DEFAULT", "set-default"),
    ("SET NULL", "set-null"),
)
@parametrize_cases("trigger", ("DELETE", "delete"), ("UPDATE", "update"))
def test_valid_fk_action_single(action: str, trigger: str) -> None:
    """Parse supported ON DELETE and ON UPDATE actions."""
    key = parse_key_declaration(
        f"FOREIGN KEY id REFERENCES dbo.users(id) ON {trigger} {action}"
    )

    assert isinstance(key, ForeignKey)
    if trigger == "DELETE":
        assert key.on_delete == action
        assert key.on_update == "NO ACTION"
    else:
        assert key.on_update == action
        assert key.on_delete == "NO ACTION"


def test_valid_fk_action_both() -> None:
    """Parse ON DELETE and ON UPDATE clauses in the same declaration."""
    key = parse_key_declaration(
        "FOREIGN KEY id REFERENCES dbo.users(id) "
        "ON DELETE SET NULL ON UPDATE CASCADE"
    )

    assert isinstance(key, ForeignKey)
    assert key.on_delete == "SET NULL"
    assert key.on_update == "CASCADE"


def test_valid_fk_action_reversed() -> None:
    """Parse ON UPDATE before ON DELETE."""
    key = parse_key_declaration(
        "FOREIGN KEY id REFERENCES dbo.users(id) "
        "ON UPDATE SET NULL ON DELETE SET DEFAULT"
    )

    assert isinstance(key, ForeignKey)
    assert key.on_delete == "SET DEFAULT"
    assert key.on_update == "SET NULL"


def test_valid_fk_action_cases() -> None:
    """Parse case-insensitive ON DELETE/UPDATE clauses and actions."""
    key = parse_key_declaration(
        "FOREIGN KEY id REFERENCES dbo.users(id) "
        "on delete set null On Update No Action"
    )

    assert isinstance(key, ForeignKey)
    assert key.on_delete == "SET NULL"
    assert key.on_update == "NO ACTION"


def test_valid_fk_action_directly_after_bracket() -> None:
    """Parse an action directly following column brackets."""
    key = parse_key_declaration(
        "FOREIGN KEY id REFERENCES dbo.users(id)ON DELETE CASCADE"
    )

    assert isinstance(key, ForeignKey)
    assert key.referenced_columns == ["id"]
    assert key.on_delete == "CASCADE"


@parametrize_cases(
    "action",
    ("ON DELETE RESTRICT", "unsupported"),
    ("ON UPDATE SET", "incomplete"),
    ("ON DELETE CASCADE SET NULL", "multiple"),
)
def test_invalid_fk_action(action: str) -> None:
    """Reject unsupported or incomplete referential actions."""
    reject(f"FOREIGN KEY id REFERENCES dbo.users(id) {action}", MSG_FK_ACTION)


@parametrize_cases(
    "declaration",
    (
        (
            "FOREIGN KEY id REFERENCES dbo.users(id) "
            "ON DELETE CASCADE ON DELETE SET NULL"
        ),
        "delete",
    ),
    (
        (
            "FOREIGN KEY id REFERENCES dbo.users(id) "
            "ON UPDATE CASCADE ON UPDATE SET NULL"
        ),
        "update",
    ),
)
def test_invalid_fk_multiple_action_clauses(declaration: str) -> None:
    """Reject duplicate actions for the same trigger."""
    reject(declaration, MSG_FK_MULTIPLE_TRIGGERS)


def test_valid_fk_references_on_identifier() -> None:
    """Parse 'on' as an identifier."""
    key = parse_key_declaration("FOREIGN KEY id REFERENCES on.users(id)")

    assert isinstance(key, ForeignKey)
    assert key.referenced_table.schema == "on"

    key = parse_key_declaration(
        "FOREIGN KEY id REFERENCES dbo.on(id) ON DELETE CASCADE"
    )

    assert isinstance(key, ForeignKey)
    assert key.referenced_table.name == "on"
    assert key.on_delete == "CASCADE"
