# Copyright 2026 Christophe Le Douarec
"""Cognitive complexity of Python source code, computed with complexipy."""

from __future__ import annotations

from dataclasses import dataclass

from complexipy import code_complexity


@dataclass(frozen=True)
class FunctionComplexity:
    """Cognitive complexity of one function or method."""

    name: str
    complexity: int
    line_start: int


def analyze_source(source: str) -> list[FunctionComplexity] | None:
    """Return the complexity of every function in ``source``.

    Args:
        source: Python source code.

    Returns:
        One entry per function, or ``None`` when complexipy cannot parse the
        code (Python 2 syntax, truncated file...), so callers can record the
        failure without aborting.
    """
    try:
        result = code_complexity(source)
    except ValueError:  # complexipy reports parse errors as ValueError
        return None
    return [
        FunctionComplexity(
            name=f.name,
            complexity=f.complexity,
            line_start=f.line_start,
        )
        for f in result.functions
    ]
