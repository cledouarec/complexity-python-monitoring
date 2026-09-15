# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

from complexity_python_monitoring.analyzer import analyze_source
from tests.samples import BRANCHY, INVALID, NESTED, SIMPLE


def test_analyze_source_reports_each_function():
    result = analyze_source(SIMPLE + "\n" + BRANCHY)
    assert result is not None
    assert [(f.name, f.complexity) for f in result] == [
        ("simple", 0),
        ("branchy", 6),
    ]
    assert result[1].line_start == 4


def test_analyze_source_handles_methods_and_nesting():
    result = analyze_source(
        "class A:\n"
        + "".join("    " + line + "\n" for line in NESTED.splitlines()),
    )
    assert result is not None
    assert [(f.name, f.complexity) for f in result] == [("A::nested", 3)]


def test_analyze_source_returns_none_on_syntax_error():
    assert analyze_source(INVALID) is None


def test_analyze_source_empty_module_has_no_functions():
    assert analyze_source("x = 1\n") == []
