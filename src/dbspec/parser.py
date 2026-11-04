"""DBSpec parser utilities.

Utilities for parsing DBSpec files into database schema model objects.
"""

import re

from dbspec.errors import DBSpecParseError
from dbspec.models import (
    Column,
    ForeignKey,
    Identity,
    Key,
    PrimaryKey,
    Table,
    TableName,
    UniqueKey,
)

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

VALID_SCHEMA_TABLE = rf"({VALID_IDENTIFIER})\.({VALID_IDENTIFIER})"

# in a CSV identifier list, at least one valid identifier
# is required; any others must be comma-separated
CSV_IDENTIFIER_LIST = rf"{VALID_IDENTIFIER}(?:\s*,\s*{VALID_IDENTIFIER})*"

FOREIGN_KEY_ACTION = r"(?:CASCADE|NO\s+ACTION|SET\s+DEFAULT|SET\s+NULL)"


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


def _parse_csv_identifier_list(value: str, name: str) -> list[str]:
    """Parse a comma-separated list of identifiers.

    Args:
        value: The comma-separated list of identifiers to parse.
        name: The name of the list being parsed, used in error messages.

    Returns:
        A list of individual identifiers extracted from the input value.

    Raises:
        DBSpecParseError: If the provided value is not a valid comma-
          separated list of valid identifiers.
    """
    # match either a bare or parenthesized list
    groups = _extract_fullmatch_groups(
        rf"(?:({CSV_IDENTIFIER_LIST})|\(\s*({CSV_IDENTIFIER_LIST})\s*\))",
        value,
        f"Invalid {name}: {value!r}",
        flags=re.IGNORECASE,
    )
    identifier_list = groups[0] or groups[1]

    return re.findall(VALID_IDENTIFIER, identifier_list, flags=re.IGNORECASE)


def parse_column_declaration(declaration: str) -> Column:  # noqa: C901
    """Parse a column declaration into a `Column` object.

    See `docs/columns.md` for the expected syntax.
    """
    # handle empty declaration
    declaration = declaration.strip()
    if not declaration:
        msg = "Column declaration cannot be empty"
        raise DBSpecParseError(msg)

    # mask bracketed identifiers and string literals (with
    # '' escapes), so keywords inside them are ignored;
    # replace with underscores of the same length,
    # so match positions still index into `declaration`
    masked = re.sub(
        rf"{BRACKETED_IDENTIFIER}|'(?:[^']|'')*'",
        lambda m: "_" * len(m.group()),
        declaration,
    )

    # find first occurrence of each keyword, to separate
    # <column_name> <data_type> portion, and identify
    # <expression> associated with each keyword
    keyword_regexes = {
        "nullability": r"(?:NOT\s+)?NULL",
        "identity": r"IDENTITY",
        "default": r"DEFAULT",
    }
    keyword_matches = {
        keyword: re.search(rf"(?<!\S){regex}\b", masked, flags=re.IGNORECASE)
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


def parse_key_declaration(declaration: str) -> Key:  # noqa: C901
    """Parse a key declaration into a `Key` object.

    See `docs/keys.md` for the expected syntax.
    """
    # handle empty declaration
    declaration = declaration.strip()
    if not declaration:
        msg = "Key declaration cannot be empty"
        raise DBSpecParseError(msg)

    # mask bracketed identifiers,
    # so keywords inside them are ignored;
    # replace with underscores of the same length,
    # so match positions still index into `declaration`
    declaration_masked = re.sub(
        BRACKETED_IDENTIFIER, lambda m: "_" * len(m.group()), declaration
    )

    # identify position of any key-type keywords,
    # verifying that there is only one,
    # and that it is correctly placed at the start
    keyword_regexes = {
        "primary": r"PRIMARY\s+KEY",
        "unique": r"UNIQUE",
        "foreign": r"FOREIGN\s+KEY",
    }
    keyword_matches = [
        (keyword, match)
        for keyword, regex in keyword_regexes.items()
        for match in re.finditer(
            rf"(?<!\S){regex}\b", declaration_masked, flags=re.IGNORECASE
        )
    ]
    if len(keyword_matches) != 1:
        msg = (
            "Key declaration must contain exactly one occurrence of "
            "PRIMARY KEY, UNIQUE, or FOREIGN KEY"
        )
        raise DBSpecParseError(msg)
    key_type, match = keyword_matches[0]
    if match.start() != 0:
        msg = (
            "Key declaration must start with "
            "PRIMARY KEY, UNIQUE, or FOREIGN KEY"
        )
        raise DBSpecParseError(msg)

    # extract the post-key portion of the declaration
    expression = declaration[match.end() :].strip()

    # handle the identified key type
    if key_type == "primary":
        columns = _parse_csv_identifier_list(
            expression, "PRIMARY KEY <column_list>"
        )
        return PrimaryKey(columns=columns)

    if key_type == "unique":
        columns = _parse_csv_identifier_list(
            expression, "UNIQUE <column_list>"
        )
        return UniqueKey(columns=columns)

    # it must be a foreign key if we reach this point

    # extract the masked post-key portion
    expression_masked = declaration_masked[match.end() :].strip()

    # identify required REFERENCES keyword
    # don't require leading space, allow punctuation
    references_matches = list(
        re.finditer(r"\bREFERENCES\b", expression_masked, flags=re.IGNORECASE)
    )
    if len(references_matches) != 1:
        msg = (
            "Foreign key declaration must contain "
            "exactly one REFERENCES keyword"
        )
        raise DBSpecParseError(msg)
    references_match = references_matches[0]

    # split either side of REFERENCES keyword
    column_list_part = expression[: references_match.start()].strip()
    references_part = expression[references_match.end() :].strip()
    references_part_masked = expression_masked[
        references_match.end() :
    ].strip()

    # parse (local) column list part
    columns = _parse_csv_identifier_list(
        column_list_part, "FOREIGN KEY <column_list>"
    )

    # identify optional ON DELETE/UPDATE trigger clauses
    trigger_regexes = {
        "delete": r"ON\s+DELETE",
        "update": r"ON\s+UPDATE",
    }
    trigger_matches = {
        trigger: list(
            re.finditer(
                rf"\b{regex}\b", references_part_masked, flags=re.IGNORECASE
            )
        )
        for trigger, regex in trigger_regexes.items()
    }
    has = {
        trigger: bool(matches) for trigger, matches in trigger_matches.items()
    }

    # ensure each trigger clause occurs at most once
    for trigger, matches in trigger_matches.items():
        if len(matches) > 1:
            msg = (
                "Foreign key declaration cannot contain "
                f"multiple ON {trigger.upper()} clauses"
            )
            raise DBSpecParseError(msg)
    trigger_matches = {
        trigger: matches[0]
        for trigger, matches in trigger_matches.items()
        if matches
    }

    # sort trigger matches by position in declaration
    ordered_matches = sorted(
        trigger_matches.items(), key=lambda item: item[1].start()
    )

    # extract and validate <schema>.<table_name>(<column_list>) portion
    reference_target = (
        references_part[: ordered_matches[0][1].start()].strip()
        if ordered_matches
        else references_part
    )
    (referenced_schema, referenced_table_name, referenced_column_list) = (
        _extract_fullmatch_groups(
            rf"{VALID_SCHEMA_TABLE}(\s+.*|\s*\(.*|)",
            reference_target,
            f"Invalid REFERENCES target: {reference_target!r}",
            flags=re.IGNORECASE,
        )
    )
    referenced_table = TableName(
        schema=referenced_schema, name=referenced_table_name
    )
    referenced_columns = _parse_csv_identifier_list(
        referenced_column_list.strip(), "REFERENCES <column_list>"
    )

    # extract, validate and normalise <action>
    # associated with each trigger clause
    trigger_expressions = {
        trigger: references_part[
            match.end() : (
                ordered_matches[i + 1][1].start()
                if i + 1 < len(ordered_matches)
                else None
            )
        ].strip()
        for i, (trigger, match) in enumerate(ordered_matches)
    }
    actions = dict.fromkeys(trigger_regexes, "NO ACTION")
    for trigger in actions:
        if not has[trigger]:
            continue
        (action,) = _extract_fullmatch_groups(
            rf"({FOREIGN_KEY_ACTION})",
            trigger_expressions[trigger],
            (
                f"Invalid ON {trigger.upper()} action: "
                f"{trigger_expressions[trigger]!r}"
            ),
            flags=re.IGNORECASE,
        )
        actions[trigger] = " ".join(action.upper().split())

    return ForeignKey(
        columns=columns,
        referenced_table=referenced_table,
        referenced_columns=referenced_columns,
        on_delete=actions["delete"],
        on_update=actions["update"],
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
