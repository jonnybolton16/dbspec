"""DBSpec test utilities."""

from typing import Any

import pytest


# -------
# Helpers
# -------
def parametrize_cases(
    argnames: str | tuple[str, ...], *cases: tuple[Any, str]
) -> pytest.MarkDecorator:
    """Parametrize a test using value/id case tuples.

    Both single- and multi-valued `cases` are supported, in the form:
    - single: `(value, id)`, where `value` is a single object (which may
      itself be a tuple)
    - multi: `(values, id)`, where `values` is a tuple of objects

    Single-valued cases are indicated by a single-string `argnames`. In
    this case, if `value` is a tuple, it is not unpacked, and is instead
    treated as the single value for the single argument.

    Multi-valued cases are indicated by a tuple-of-strings `argnames`.
    In this case, the `values` tuple is unpacked, with each value
    corresponding to the same-index argument.

    In either case, `id` is an id string for the test case.
    """
    multi = isinstance(argnames, tuple)

    return pytest.mark.parametrize(
        argnames,
        [
            pytest.param(*(values if multi else (values,)), id=case_id)
            for values, case_id in cases
        ],
    )


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
