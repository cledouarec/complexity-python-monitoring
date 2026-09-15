# Copyright 2026 Christophe Le Douarec
"""Descriptive statistics of a complexity population."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime


@dataclass(frozen=True)
class Summary:
    """Mean, median, deciles and extrema of a population."""

    count: int
    mean: float
    median: float
    p10: float
    p90: float
    min: int
    max: int


@dataclass(frozen=True)
class TrendPoint:
    """The complexity summary of one commit, positioned in time."""

    date: datetime
    summary: Summary


def summarize(values: Sequence[int]) -> Summary:
    """Compute the mean, median, deciles and extrema of ``values``.

    Args:
        values: Per-function complexities.

    Returns:
        The descriptive statistics of the population.

    Raises:
        ValueError: If ``values`` is empty.
    """
    if not values:
        message = "cannot summarize an empty population"
        raise ValueError(message)
    arr = np.asarray(values, dtype=float)
    p10, median, p90 = np.percentile(arr, [10, 50, 90])
    return Summary(
        count=int(arr.size),
        mean=float(arr.mean()),
        median=float(median),
        p10=float(p10),
        p90=float(p90),
        min=int(arr.min()),
        max=int(arr.max()),
    )
