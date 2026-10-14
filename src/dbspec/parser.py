"""DBSpec parser utilities.

Utilities for parsing DBSpec files into database schema model objects.
"""

import re

from dbspec.errors import DBSpecParseError
from dbspec.models import Column, Identity, Table, TableName

# match valid schema/table/column identifiers (`docs/identifiers.md`)
BRACKETED_IDENTIFIER = r"\[(?:[^\]]|\]\])+\]"
VALID_IDENTIFIER = rf"(?:[A-Z_][A-Z0-9_]*|{BRACKETED_IDENTIFIER})"
# (?:X|Y) -> either X or Y
# X = [A-Z_][A-Z0-9_]*
# [A-Z_] -> a letter (case-insensitive with re.IGNORECASE) or underscore
# [A-Z0-9_]* -> zero or more word (alphanumeric/underscore) characters
# X -> at least one word character, but not starting with a number
# Y = \[(?:[^\]]|\]\])+\]
# \[...\] -> matched square brackets
# (?:x|y)+ -> one or more occurrences of x or y
# x = [^\]] -> any character except a closing square bracket
# y = \]\] -> an escaped closing square bracket
# Y -> at least one character enclosed in square brackets, allowing
#      escaped closing square brackets with ]]


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
    """Parse a column declaration into a `Column` object.

    See `docs/columns.md` for the expected syntax.
    """
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
    # mask bracketed identifiers and string literals (with
    # '' escapes), so keywords inside them are ignored;
    # replace with underscores of the same length,
    # so match positions still index into `declaration`
    masked = re.sub(
        rf"{BRACKETED_IDENTIFIER}|'(?:[^']|'')*'",
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
        rf"({VALID_IDENTIFIER})\s+(.+)",
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

    See `docs/tables.md` for the expected syntax.
    """
    schema, name = _extract_fullmatch_groups(
        rf"TABLE\s+({VALID_IDENTIFIER})\.({VALID_IDENTIFIER})",
        declaration.strip(),
        f"Invalid table declaration: {declaration!r}",
        flags=re.IGNORECASE,
    )
    identifier = TableName(schema=schema, name=name)
    return Table(identifier=identifier)
