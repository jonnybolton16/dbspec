"""DBSpec test utilities."""

from collections.abc import Iterable
from typing import Any

import pytest


# -------
# Helpers
# -------
def case_params(cases: Iterable[tuple[Any, str]]) -> list[pytest.ParameterSet]:
    """Convert value/id case tuples into pytest parameter sets.

    Both single- and multi-valued cases are supported, in the form:
    - single: `(value, id)`, `value` is a single object
    - multi: `((values...), id)`, `values` is a tuple of objects
    """
    return [
        pytest.param(
            *(values if isinstance(values, tuple) else (values,)), id=case_id
        )
        for values, case_id in cases
    ]


# ----------
# Whitespace
# ----------
WHITESPACE_SEPARATORS = [
    (" ", "single-space"),
    ("    ", "multiple-spaces"),
    ("\t", "tab"),
    (" \t ", "mixed"),
]


# -----------
# Identifiers
# -----------
VALID_IDENTIFIERS = [
    ("dbo", "lowercase-letters"),
    ("MY_TABLE", "uppercase-letters-and-underscores"),
    ("Column0123456789", "mixed-case-letters-and-digits"),
    ("_orgs", "leading-underscore"),
    ("[dbo]", "unnecessary-brackets"),
    ("[123abc]", "leading-digit-with-brackets"),
    ("[café]", "non-ascii-with-brackets"),
    ("[aB '5~@]]#)]", "other-characters-with-brackets"),
]
INVALID_IDENTIFIERS = [
    ("[]", "empty-with-brackets"),
    ("123abc", "leading-digit-without-brackets"),
    ("café", "non-ascii-without-brackets"),
    ("aB '5~@]]#)", "other-characters-without-brackets"),
    ("[aB '5~@]#)]", "unescaped-closing-bracket"),
    ("123abc]", "missing-opening-bracket"),
    ("[123abc", "missing-closing-bracket"),
    ("[[123abc]]", "trailing-escaped-closing-bracket"),
]
