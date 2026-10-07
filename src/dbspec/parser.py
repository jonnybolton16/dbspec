"""DBSpec parser utilities.

Utilities for parsing DBSpec files into database schema model objects.
"""

import re

from dbspec.errors import DBSpecParseError
from dbspec.models import Column, Identity, Table


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


def parse_column_declaration(declaration: str) -> Column:  # noqa: C901
    # ruff: disable[E501,W505]
    """Parse a column declaration into a `Column` object.

    Column declarations are expected to be of the form:

        <column_name> <data_type> {[NOT] NULL [DEFAULT <expression>] | IDENTITY[(<seed>, <increment>)]}

    For example:

        ???

    Note:
    - The `NOT`, `NULL`, `DEFAULT`, and `IDENTITY` keywords are
    case-insensitive.
    - If the column name contains whitespace, it must be enclosed by
    square brackets. In such cases, the name itself cannot contain
    nested square brackets.
    - All column declarations other than `IDENTITY` columns must specify
    their nullability explicitly. `IDENTITY` columns are implicitly NOT
    NULL.
    - When using the `IDENTITY` option, neither or both the seed and
    increment must be provided. If they are provided, they must be
    integers. If they are not provided, they are defaulted to 1.
    - When using the `DEFAULT` option, the expression cannot be empty.
    The clause must follow the nullability specification, because `NULL`
    itself can appear in the `DEFAULT` expression. The validity of the
    expression is checked by SQL Server at execution time, not at parse
    time.
    """
    # ruff: enable[E501,W505]
    # handle empty declaration
    declaration = declaration.strip()
    if not declaration:
        msg = "Column declaration cannot be empty"
        raise DBSpecParseError(msg)

    # find first occurrence of each keyword, to separate
    # <column_name> <data_type> portion, and identify
    # <expression> associated with each keyword
    keyword_regexes = {
        "nullability": r"(?:NOT\s+)?NULL",
        "identity": r"IDENTITY",
        "default": r"DEFAULT",
    }
    # mask bracketed names and string literals (with '' escapes),
    # so keywords inside them are ignored;
    # replace with underscores of the same length,
    # so match positions still index into `declaration`
    masked = re.sub(
        r"\[[^\[\]]*\]|'(?:[^']|'')*'",
        lambda m: "_" * len(m.group()),
        declaration,
    )
    keyword_matches = {
        keyword: re.search(
            rf"(?<!\S){regex}\b",
            masked,
            flags=re.IGNORECASE,
        )
        for keyword, regex in keyword_regexes.items()
    }
    has = {keyword: bool(match) for keyword, match in keyword_matches.items()}

    # sort keyword matches by position in declaration
    ordered_matches = sorted(
        filter(lambda item: item[1], keyword_matches.items()),
        key=lambda item: item[1].start(),
    )

    # extract <column_name> <data_type> portion
    name_type = (
        declaration[: ordered_matches[0][1].start()].strip()
        if ordered_matches
        else declaration
    )

    # extract <expression> associated with each keyword
    keyword_expressions = {
        keyword: declaration[
            match.end() : (
                ordered_matches[i + 1][1].start()
                if i + 1 < len(ordered_matches)
                else None
            )
        ].strip()
        for i, (keyword, match) in enumerate(ordered_matches)
    }

    # validate <column_name> <data_type> format,
    # allowing for bracketed <column_name>;
    # do this before validating any clauses,
    # so that missing name/type errors take precedence
    column_name, data_type = _extract_fullmatch_groups(
        r"(\[[^\[\]]+\]|[^\s\[\]]+)\s+(.+)",
        name_type,
        f"Missing/invalid <column_name> and/or <data_type>: {name_type!r}",
        flags=re.IGNORECASE,
    )

    # validate keyword combinations
    if not (has["nullability"] or has["identity"]):
        msg = "Missing NULL/NOT NULL or IDENTITY clause"
        raise DBSpecParseError(msg)
    if has["identity"]:
        mutually_exclusive = {
            "nullability": "NULL/NOT NULL",
            "default": "DEFAULT",
        }
        for keyword, name in mutually_exclusive.items():
            if has[keyword]:
                msg = f"IDENTITY and {name} clauses are mutually exclusive"
                raise DBSpecParseError(msg)
    if (
        has["nullability"]
        and has["default"]
        and (
            keyword_matches["default"].start()
            < keyword_matches["nullability"].start()
        )
    ):
        msg = "DEFAULT clause cannot precede NULL/NOT NULL clause"
        raise DBSpecParseError(msg)

    # validate keyword expressions
    if has["nullability"]:
        if nullability_expression := keyword_expressions["nullability"]:
            msg = (
                "Unexpected expression after NULL/NOT NULL clause: "
                f"{nullability_expression!r}"
            )
            raise DBSpecParseError(msg)
        nullable = keyword_matches["nullability"].group().upper() == "NULL"
        identity = None

    if has["identity"]:
        if identity_expression := keyword_expressions["identity"]:
            groups = _extract_fullmatch_groups(
                r"\(\s*([+-]?[0-9]+)\s*,\s*([+-]?[0-9]+)\s*\)",
                identity_expression,
                f"Invalid IDENTITY specification: {identity_expression!r}",
            )
            seed, increment = map(int, groups)
            identity = Identity(seed=seed, increment=increment)
        else:
            identity = Identity()
        nullable = False

    default_expression = keyword_expressions.get("default")
    if has["default"] and not default_expression:
        msg = "Missing DEFAULT expression"
        raise DBSpecParseError(msg)

    return Column(
        name=column_name,
        datatype=data_type,
        nullable=nullable,
        identity=identity,
        default=default_expression,
    )


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
