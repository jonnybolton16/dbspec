"""DBSpec column declaration parser tests."""

import pytest

from dbspec.errors import DBSpecParseError
from dbspec.models import Column, Identity
from dbspec.parser import parse_column_declaration
from tests.utils import (
    EMPTY_DECLARATIONS,
    INVALID_IDENTIFIERS,
    VALID_IDENTIFIERS,
    WHITESPACE_SEPARATORS,
    parametrize_cases,
)

# use a simple valid prefix whenever the test is
# about clauses rather than column name/type extraction
SIMPLE_NAME = "id"
SIMPLE_TYPE = "INT"
SIMPLE_NAME_TYPE = f"{SIMPLE_NAME} {SIMPLE_TYPE}"

# use a simple nullability clause whenever the test is
# about column name/type extractions rather than clauses
SIMPLE_NULL_CLAUSE = "NULL"
SIMPLE_NULL_VALUE = True


# ---------------------
# Error message regexes
# ---------------------
MSG_EMPTY = "Column declaration cannot be empty"
MSG_NAME_TYPE = "Missing/invalid <column_name> and/or <data_type>"
MSG_MISSING_REQUIRED = "Missing NULL/NOT NULL or IDENTITY clause"
MSG_MUTUAL_EXCLUSION = (
    r"IDENTITY and (NULL/NOT NULL|DEFAULT) clauses are mutually exclusive"
)
MSG_DEFAULT_ORDER = "DEFAULT clause cannot precede NULL/NOT NULL clause"
MSG_NULL_EXPRESSION = "Unexpected expression after NULL/NOT NULL clause"
MSG_IDENTITY_SPEC = "Invalid IDENTITY specification"
MSG_MISSING_DEFAULT = "Missing DEFAULT expression"


# -------------------------
# Rejection helper function
# -------------------------
def reject(declaration: str, message: str) -> None:
    """Reject a column declaration with the expected error message."""
    with pytest.raises(DBSpecParseError, match=message):
        parse_column_declaration(declaration)


# ----------------------------------
# Empty/whitespace-only declarations
# ----------------------------------
@parametrize_cases("declaration", *EMPTY_DECLARATIONS)
def test_invalid_empty_declaration(declaration: str) -> None:
    """Reject an empty/whitespace-only column declaration."""
    reject(declaration, MSG_EMPTY)


# -------------------------
# Column name and data type
# -------------------------
### valid name/type ###
@parametrize_cases(
    ("name_type", "expected_name", "expected_datatype"),
    ((SIMPLE_NAME_TYPE, SIMPLE_NAME, SIMPLE_TYPE), "simple"),
    *(
        (
            (f"{name} {SIMPLE_TYPE}", name, SIMPLE_TYPE),
            f"name-identifier_{case_id}",
        )
        for name, case_id in VALID_IDENTIFIERS
    ),
    (
        (f"aB '5~@]]#) {SIMPLE_TYPE}", "aB", f"'5~@]]#) {SIMPLE_TYPE}"),
        "missing-opening-bracket",
    ),  # included as type currently accepts "'5~@]]#) <SIMPLE_TYPE>"
    (
        (f"{SIMPLE_NAME} NVARCHAR(100)", SIMPLE_NAME, "NVARCHAR(100)"),
        "type-with-parameter",
    ),
    (
        (f"{SIMPLE_NAME} DECIMAL(10, 2)", SIMPLE_NAME, "DECIMAL(10, 2)"),
        "type-parameter-with-whitespace",
    ),
    *(
        (
            (f"{SIMPLE_NAME}{sep}{SIMPLE_TYPE}", SIMPLE_NAME, SIMPLE_TYPE),
            f"separator_{case_id}",
        )
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_name_type(
    name_type: str, expected_name: str, expected_datatype: str
) -> None:
    """Parse the column name and data type, preserving brackets."""
    column = parse_column_declaration(f"{name_type} {SIMPLE_NULL_CLAUSE}")

    assert column.name == expected_name
    assert column.datatype == expected_datatype


### column name contains keyword ###
@parametrize_cases(
    "name",
    # keywords as a substring
    ("nullable", "null-substring"),
    ("not_null", "not-null-substring"),
    ("default_value", "default-substring"),
    ("identity_col", "identity-substring"),
    # keywords as separate words inside brackets
    ("[null]", "bracketed-only"),
    ("[default name]", "bracketed-first"),
    ("[user identity]", "bracketed-last"),
    ("[a not null column]", "bracketed-mid"),
)
def test_valid_keyword_like_name(name: str) -> None:
    """Parse a keyword-like column name."""
    column = parse_column_declaration(
        f"{name} {SIMPLE_TYPE} {SIMPLE_NULL_CLAUSE}"
    )

    assert column.name == name


### invalid name/type ###
@parametrize_cases(
    "name_type",
    ("", "blank"),
    ("idINT", "single-token"),
    *(
        (
            f"{name} {SIMPLE_TYPE}",
            f"name-identifier_{case_id}",
        )
        for name, case_id in INVALID_IDENTIFIERS
        if name != "aB '5~@]]#)"
        # excluded as type currently accepts "'5~@]]#) <SIMPLE_TYPE>"
    ),
    (f"DEFAULT {SIMPLE_TYPE}", "keyword-name-upper"),
    (f"not null {SIMPLE_TYPE}", "keyword-name-lower"),
    (f"Identity {SIMPLE_TYPE}", "keyword-name-mixed"),
)
def test_invalid_name_type(name_type: str) -> None:
    """Reject a missing/invalid column name and/or data type."""
    reject(f"{name_type} {SIMPLE_NULL_CLAUSE}", MSG_NAME_TYPE)


# -----------
# Nullability
# -----------
### valid nullability ###
@parametrize_cases(
    ("clause", "expected"),
    (("NULL", True), "null"),
    (("NOT NULL", False), "not-null"),
    (("null", True), "lower"),
    (("nOt NuLl", False), "mixed"),
    *(
        (
            (f"NOT{sep}NULL", False),
            f"separator_{case_id}",
        )
        for sep, case_id in WHITESPACE_SEPARATORS
    ),
)
def test_valid_nullability(clause: str, *, expected: bool) -> None:
    """Parse the nullability clause."""
    column = parse_column_declaration(f"{SIMPLE_NAME_TYPE} {clause}")

    assert column.nullable is expected
    assert column.default is None
    assert column.identity is None


### invalid nullability ###
@parametrize_cases(
    "clause",
    ("NULL foo", "expression-after-null"),
    ("NOT NULL foo", "expression-after-not-null"),
    ("NULL foo DEFAULT bar", "expression-between-null-and-default"),
    ("NOT NULL (foo + bar) DEFAULT baz", "parenthesised-expression"),
)
def test_invalid_nullability(clause: str) -> None:
    """Reject an invalid nullability clause."""
    reject(f"{SIMPLE_NAME_TYPE} {clause}", MSG_NULL_EXPRESSION)


# -------
# Default
# -------
### valid default expressions ###
# representative free-form expressions
# keywords can be included inside '...' literals
# expression validation is left to SQL
@parametrize_cases(
    "expression",
    ("foo", "single-token"),
    ("foo bar", "whitespace"),
    ("foo.bar.baz", "dot-notation"),
    ("[foo bar]", "square-brackets"),
    ("(foo + bar)", "parenthesised-expression"),
    ("0", "numeric-literal"),
    ("SYSDATETIME()", "function-call"),
    ("ISNULL(foo, 0)", "keyword-in-function-name"),
    ("'foo bar'", "string-literal"),
    ("''", "empty-string-literal"),
    ("'a''b'", "escaped-single-quote"),
    ("'NULL'", "quoted-keyword-only"),
    ("'DEFAULT NAME'", "quoted-keyword-first"),
    ("'USER IDENTITY'", "quoted-keyword-last"),
    ("'A DEFAULT IDENTITY EXPRESSION'", "quoted-keyword-mid"),
    ("NULL", "null-expression"),
    ("CASE WHEN foo THEN bar ELSE NULL END", "null-in-expression"),
)
def test_valid_default_expression(expression: str) -> None:
    """Parse the default clause."""
    column = parse_column_declaration(
        f"{SIMPLE_NAME_TYPE} {SIMPLE_NULL_CLAUSE} DEFAULT {expression}"
    )

    assert column.nullable is SIMPLE_NULL_VALUE
    assert column.default == expression
    assert column.identity is None


### case-insensitivity ###
@parametrize_cases(
    "keyword",
    ("DEFAULT", "upper"),
    ("default", "lower"),
    ("Default", "mixed"),
)
def test_valid_default_case(keyword: str) -> None:
    """Parse a case-insensitive default keyword."""
    column = parse_column_declaration(
        f"{SIMPLE_NAME_TYPE} {SIMPLE_NULL_CLAUSE} {keyword} foo"
    )

    assert column.nullable is SIMPLE_NULL_VALUE
    assert column.default == "foo"
    assert column.identity is None


### flexible whitespace ###
@parametrize_cases("separator", *WHITESPACE_SEPARATORS)
def test_valid_default_separator(separator: str) -> None:
    """Parse a default clause with a flexible whitespace separator."""
    column = parse_column_declaration(
        f"{SIMPLE_NAME_TYPE} {SIMPLE_NULL_CLAUSE} DEFAULT{separator}foo"
    )

    assert column.nullable is SIMPLE_NULL_VALUE
    assert column.default == "foo"
    assert column.identity is None


### missing default expression ###
def test_invalid_default() -> None:
    """Reject a missing default expression."""
    reject(
        f"{SIMPLE_NAME_TYPE} {SIMPLE_NULL_CLAUSE} DEFAULT", MSG_MISSING_DEFAULT
    )


# --------
# Identity
# --------
### valid identity specifications ###
@parametrize_cases(
    ("spec", "expected"),
    (("", (1, 1)), "no-spec-default"),
    (("(1,1)", (1, 1)), "no-spaces"),
    ((" (1,1)", (1, 1)), "space-before-parenthesis"),
    (("(1, 1)", (1, 1)), "space-after-comma"),
    ((" ( 1 , 1 )", (1, 1)), "flexible-whitespace"),
    (("(-2, 3)", (-2, 3)), "negative-seed"),
    (("(3, -2)", (3, -2)), "negative-increment"),
    (("(+5, 10)", (5, 10)), "explicit-positive-seed"),
    (("(5, +10)", (5, 10)), "explicit-positive-increment"),
)
def test_valid_identity_spec(spec: str, expected: tuple) -> None:
    """Parse the identity clause."""
    column = parse_column_declaration(f"{SIMPLE_NAME_TYPE} IDENTITY{spec}")

    assert column.nullable is False
    assert column.default is None
    assert column.identity == Identity(*expected)


### case-insensitivity ###
@parametrize_cases(
    "keyword",
    ("IDENTITY", "upper"),
    ("identity", "lower"),
    ("Identity", "mixed"),
)
def test_valid_identity_case(keyword: str) -> None:
    """Parse a case-insensitive identity keyword."""
    column = parse_column_declaration(f"{SIMPLE_NAME_TYPE} {keyword}")

    assert column.nullable is False
    assert column.default is None
    assert column.identity == Identity()


### invalid identity specifications ###
@parametrize_cases(
    "spec",
    ("()", "no-arguments"),
    ("(1)", "one-argument"),
    ("(1,2,3)", "three-arguments"),
    ("(,1)", "missing-seed"),
    ("(1,)", "missing-increment"),
    ("(1.5,1)", "decimal-seed"),
    ("(1,1.5)", "decimal-increment"),
    ("(+,1)", "sign-only-seed"),
    ("(1,-)", "sign-only-increment"),
    ("(a,1)", "non-numeric-seed"),
    ("(1,a)", "non-numeric-increment"),
    (" 1,1", "missing-parentheses"),
    (" 1,1)", "missing-opening-parenthesis"),
    ("(1,1", "missing-closing-parenthesis"),
    ("(1 1)", "missing-comma"),
    ("(1,1) foo", "trailing-token"),
    (" foo", "single-token"),
)
def test_invalid_identity(spec: str) -> None:
    """Reject an invalid identity specification."""
    reject(f"{SIMPLE_NAME_TYPE} IDENTITY{spec}", MSG_IDENTITY_SPEC)


# --------------------------------------------
# Missing required nullability/identity clause
# --------------------------------------------
@parametrize_cases(
    "declaration",
    ("", "no-options"),
    ("DEFAULT foo", "default-only"),
)
def test_invalid_missing_required(declaration: str) -> None:
    """Reject a declaration missing NULL, NOT NULL, or IDENTITY."""
    reject(f"{SIMPLE_NAME_TYPE} {declaration}", MSG_MISSING_REQUIRED)


# --------------------------
# Mutually exclusive clauses
# --------------------------
NULL_COMPANIONS = ["NULL", "NOT NULL"]


@parametrize_cases(
    "declaration",
    # identity with either nullability, in either order
    *(
        (
            " ".join(clauses),
            "-".join(clause.lower().replace(" ", "-") for clause in clauses),
        )
        for nullability in NULL_COMPANIONS
        for clauses in [
            ["IDENTITY", nullability],
            [nullability, "IDENTITY"],
        ]
    ),
    # identity with default, in either order
    ("IDENTITY DEFAULT foo", "identity-default"),
    ("DEFAULT foo IDENTITY", "default-identity"),
    # identity with both, with default appearing after nullability
    *(
        (
            " ".join(clauses),
            "-".join(
                clause.lower().replace(" foo", "").replace(" ", "-")
                for clause in clauses
            ),
        )
        for nullability in NULL_COMPANIONS
        for clauses in [
            ["IDENTITY", nullability, "DEFAULT foo"],
            [nullability, "IDENTITY", "DEFAULT foo"],
            [nullability, "DEFAULT foo", "IDENTITY"],
        ]
    ),
)
def test_invalid_mutual_exclusions(declaration: str) -> None:
    """Reject mutually exclusive clauses."""
    reject(f"{SIMPLE_NAME_TYPE} {declaration}", MSG_MUTUAL_EXCLUSION)


# ---------------------
# Default/null ordering
# ---------------------
@parametrize_cases(
    "declaration",
    ("DEFAULT foo NULL", "default-null"),
    ("DEFAULT foo NOT NULL", "default-not-null"),
    ("DEFAULT CASE WHEN foo THEN bar ELSE NULL END", "null-in-expression"),
)
def test_invalid_default_null_ordering(declaration: str) -> None:
    """Reject a declaration where default appears before nullability."""
    reject(f"{SIMPLE_NAME_TYPE} {declaration}", MSG_DEFAULT_ORDER)


# -----------------
# Repeated keywords
# -----------------
def test_invalid_repeated_nullability_as_expression() -> None:
    """Reject a repeated NULL as an unexpected expression."""
    reject(f"{SIMPLE_NAME_TYPE} NULL NULL", MSG_NULL_EXPRESSION)


def test_valid_repeated_default_as_expression() -> None:
    """Parse a repeated DEFAULT as an expression."""
    column = parse_column_declaration(
        f"{SIMPLE_NAME_TYPE} {SIMPLE_NULL_CLAUSE} DEFAULT foo DEFAULT bar"
    )

    assert column.default == "foo DEFAULT bar"


def test_invalid_repeated_identity_as_specification() -> None:
    """Reject a repeated IDENTITY as an invalid specification."""
    reject(f"{SIMPLE_NAME_TYPE} IDENTITY IDENTITY", MSG_IDENTITY_SPEC)


# ----------------------
# Multi-error precedence
# ----------------------
@parametrize_cases(
    ("declaration", "expected_message"),
    # empty input before any parsing
    (("", MSG_EMPTY), "empty-first"),
    # invalid name/type before any clause validation
    (("idINT", MSG_NAME_TYPE), "name-type-before-missing-required"),
    (
        ("idINT IDENTITY NULL", MSG_NAME_TYPE),
        "name-type-before-mutual-exclusion",
    ),
    (
        ("idINT DEFAULT foo NOT NULL", MSG_NAME_TYPE),
        "name-type-before-default-order",
    ),
    (("idINT NULL foo", MSG_NAME_TYPE), "name-type-before-null-expression"),
    (
        ("idINT IDENTITY(1)", MSG_NAME_TYPE),
        "name-type-before-identity-specification",
    ),
    (
        ("idINT NOT NULL DEFAULT", MSG_NAME_TYPE),
        "name-type-before-missing-default",
    ),
    # missing required before missing default
    (
        (f"{SIMPLE_NAME_TYPE} DEFAULT", MSG_MISSING_REQUIRED),
        "missing-required-before-missing-default",
    ),
    # mutual exclusion before individual clause validation
    (
        (
            f"{SIMPLE_NAME_TYPE} DEFAULT foo IDENTITY NULL",
            MSG_MUTUAL_EXCLUSION,
        ),
        "mutual-exclusion-before-default-order",
    ),
    (
        (f"{SIMPLE_NAME_TYPE} NOT NULL foo IDENTITY", MSG_MUTUAL_EXCLUSION),
        "mutual-exclusion-before-null-expression",
    ),
    (
        (f"{SIMPLE_NAME_TYPE} IDENTITY(1) DEFAULT foo", MSG_MUTUAL_EXCLUSION),
        "mutual-exclusion-before-identity-specification",
    ),
    (
        (f"{SIMPLE_NAME_TYPE} IDENTITY DEFAULT", MSG_MUTUAL_EXCLUSION),
        "mutual-exclusion-before-missing-default",
    ),
    # default ordering before expression handling
    (
        (f"{SIMPLE_NAME_TYPE} DEFAULT foo NOT NULL bar", MSG_DEFAULT_ORDER),
        "default-order-before-null-expression",
    ),
    (
        (f"{SIMPLE_NAME_TYPE} DEFAULT NULL", MSG_DEFAULT_ORDER),
        "default-order-before-missing-default",
    ),
    # unexpected nullability expression before missing default
    (
        (f"{SIMPLE_NAME_TYPE} NOT NULL foo DEFAULT", MSG_NULL_EXPRESSION),
        "null-expression-before-missing-default",
    ),
)
def test_invalid_multiple_errors(
    declaration: str, expected_message: str
) -> None:
    """Reject a multiply-invalid declaration with the expected error.

    The intended error-precedence is as follows:

    1. empty declaration;
    2. missing/invalid name/data type;
    3. missing nullability or identity;
    4. mutually exclusive clauses;
    5. default before nullability;
    6. unexpected nullability expression;
    7. invalid identity specification;
    8. missing default expression.
    """
    reject(declaration, expected_message)


# -----------------------
# Full valid declarations
# -----------------------
@parametrize_cases(
    ("declaration", "expected"),
    (
        (
            "description NVARCHAR(200) NULL",
            Column(
                name="description",
                datatype="NVARCHAR(200)",
                nullable=True,
            ),
        ),
        "null-no-default",
    ),
    (
        (
            "created_at DATETIME2(3) NOT NULL DEFAULT SYSDATETIME()",
            Column(
                name="created_at",
                datatype="DATETIME2(3)",
                nullable=False,
                default="SYSDATETIME()",
            ),
        ),
        "not-null-with-default",
    ),
    (
        (
            "id BIGINT IDENTITY(100, 5)",
            Column(
                name="id",
                datatype="BIGINT",
                nullable=False,
                identity=Identity(seed=100, increment=5),
            ),
        ),
        "identity-with-values",
    ),
    (
        (
            "[display name] NVARCHAR(100) NULL DEFAULT 'Not specified'",
            Column(
                name="[display name]",
                datatype="NVARCHAR(100)",
                nullable=True,
                default="'Not specified'",
            ),
        ),
        "bracketed-name-and-string-default",
    ),
)
def test_valid_declaration(declaration: str, expected: Column) -> None:
    """Parse a full valid column declaration."""
    assert parse_column_declaration(declaration) == expected
