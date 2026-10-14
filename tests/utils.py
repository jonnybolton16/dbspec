"""DBSpec test utilities."""

from collections.abc import Iterable
from typing import Any

import pytest

WHITESPACE_SEPARATORS = [
    (" ", "single-space"),
    ("    ", "multiple-spaces"),
    ("\t", "tab"),
    (" \t ", "mixed"),
]


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
