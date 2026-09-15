# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

import pytest

from complexity_python_monitoring.stats import summarize


def test_summarize_computes_mean_and_deciles():
    values = list(range(1, 11))  # 1..10
    s = summarize(values)
    assert s.count == 10
    assert s.mean == pytest.approx(5.5)
    assert s.median == pytest.approx(5.5)
    assert s.p10 == pytest.approx(1.9)
    assert s.p90 == pytest.approx(9.1)
    assert s.max == 10
    assert s.min == 1


def test_summarize_single_value():
    s = summarize([7])
    assert (s.mean, s.p10, s.p90, s.count) == (7, 7, 7, 1)
    assert (s.min, s.median, s.max) == (7, 7, 7)


def test_summarize_rejects_empty_population():
    with pytest.raises(ValueError, match="empty"):
        summarize([])
