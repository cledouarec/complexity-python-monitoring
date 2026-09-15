# Copyright 2026 Christophe Le Douarec
"""Static charts (PNG) rendered with matplotlib on the headless Agg backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

import matplotlib as mpl

mpl.use("Agg")

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from .stats import summarize

if TYPE_CHECKING:
    from collections.abc import Sequence
    from datetime import datetime
    from pathlib import Path

    from matplotlib.axes import Axes
    from matplotlib.figure import Figure

    from .stats import TrendPoint

# Reference palette (dataviz skill): one hue per measure, text in ink tones.
SERIES = "#2a78d6"  # categorical slot 1: mean
SERIES_2 = "#eb6834"  # categorical slot 2: median
SERIES_LIGHT = "#86b6ef"  # step 250 of the slot 1 ramp: deciles
BAND = "#cde2fb"  # step 100 of the slot 1 ramp: decile band
SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_SOFT = "#52514e"
GRID = "#e6e5e1"

_MARKER_LIMIT = 60  # above this many commits, point markers only add noise


def _style(ax: Axes) -> None:
    ax.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_SOFT, labelsize=9)
    ax.yaxis.grid(visible=True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def _save(fig: Figure, out: Path | str) -> None:
    fig.savefig(out, facecolor=SURFACE)
    plt.close(fig)


# Legend entries follow the vertical order of the lines on the chart.
_TREND_LINES = (
    ("max", "Max", INK_SOFT, 1.0, ":"),
    ("p90", "9th decile", SERIES_LIGHT, 1.2, "-"),
    ("mean", "Mean", SERIES, 2.0, "-"),
    ("median", "Median", SERIES_2, 2.0, "-"),
    ("p10", "1st decile", SERIES_LIGHT, 1.2, "--"),
    ("min", "Min", INK_SOFT, 1.0, ":"),
)


def _draw_trend(
    ax: Axes,
    dates: Sequence[datetime],
    series: dict[str, list[float]],
    *,
    title: str,
    with_max: bool,
) -> None:
    """Draw the trend lines on ``ax``, optionally leaving the maximum out."""
    _style(ax)
    ax.fill_between(
        dates,
        series["p10"],
        series["p90"],
        color=BAND,
        linewidth=0,
        label="1st - 9th decile band",
    )
    for name, label, color, width, style in _TREND_LINES:
        if name == "max" and not with_max:
            continue
        ax.plot(
            dates,
            series[name],
            color=color,
            linewidth=width,
            linestyle=style,
            label=label,
        )
    if len(dates) <= _MARKER_LIMIT:
        for name, color in (("mean", SERIES), ("median", SERIES_2)):
            ax.plot(
                dates,
                series[name],
                "o",
                color=color,
                markersize=4,
                markeredgecolor=SURFACE,
            )

    for name in ("mean", "median"):
        ax.annotate(
            f"{series[name][-1]:.1f}",
            (dates[-1], series[name][-1]),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
            color=INK,
        )
    # Without the maximum, the scale follows the highest remaining line
    # (the mean can exceed P90 on heavily skewed distributions).
    top_lines = ("max",) if with_max else ("p90", "mean", "median")
    ceiling = max(1.0, *(v for name in top_lines for v in series[name]))
    # A slightly negative floor keeps a minimum sitting at 0 visible.
    ax.set_ylim(bottom=-0.02 * ceiling, top=ceiling * 1.08)
    ax.set_ylabel(
        "Cognitive complexity per function",
        color=INK_SOFT,
        fontsize=10,
    )
    ax.set_title(title, color=INK, fontsize=12, loc="left")
    ax.legend(frameon=False, fontsize=9, labelcolor=INK_SOFT, loc="upper left")


def trend_figure(
    points: Sequence[TrendPoint],
    title: str = "",
    *,
    with_max: bool = True,
) -> Figure:
    """Build the trend chart: min, deciles, median, mean and max per commit.

    Args:
        points: One summary per commit, in chronological order.
        title: Chart title; a default is used when empty.
        with_max: Draw the max line. Leaving it out keeps a few outliers
            from squashing the other lines: the scale then follows the
            9th decile.

    Returns:
        The matplotlib figure, which the caller must close.

    Raises:
        ValueError: If ``points`` is empty.
    """
    if not points:
        message = "nothing to plot"
        raise ValueError(message)
    dates = [p.date for p in points]
    series = {
        name: [getattr(p.summary, name) for p in points]
        for name in ("min", "p10", "median", "mean", "p90", "max")
    }

    fig, ax = plt.subplots(figsize=(11, 5), dpi=150, facecolor=SURFACE)
    _draw_trend(
        ax,
        dates,
        series,
        title=title or "Cognitive complexity over time",
        with_max=with_max,
    )
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(locator))
    fig.tight_layout()
    return fig


def plot_trend(
    points: Sequence[TrendPoint],
    out: Path | str,
    title: str = "",
    *,
    with_max: bool = True,
) -> None:
    """Plot min, deciles, median, mean and (optionally) max over time.

    Args:
        points: One summary per commit, in chronological order.
        out: Destination PNG file.
        title: Chart title; a default is used when empty.
        with_max: Draw the max line; see :func:`trend_figure`.
    """
    _save(trend_figure(points, title=title, with_max=with_max), out)


def commit_figure(values: Sequence[int], title: str = "") -> Figure:
    """Build the histogram of the per-function complexity of one commit.

    Args:
        values: Complexity of every function of the commit (not empty).
        title: Chart title; a default is used when empty.

    Returns:
        The matplotlib figure, which the caller must close.
    """
    s = summarize(values)
    fig, ax = plt.subplots(figsize=(10, 5), dpi=150, facecolor=SURFACE)
    _style(ax)
    ax.hist(
        values,
        bins=np.arange(-0.5, s.max + 1.5),
        color=SERIES,
        edgecolor=SURFACE,
        linewidth=1.5,
    )
    ymax = ax.get_ylim()[1]
    markers = (
        (s.mean, f"mean {s.mean:.1f}", "-"),
        (s.p90, f"P90 {s.p90:.0f}", "--"),
    )
    for value, label, style in markers:
        ax.axvline(value, color=INK_SOFT, linewidth=1, linestyle=style)
        ax.text(
            value,
            ymax * 0.98,
            f" {label}",
            color=INK_SOFT,
            fontsize=9,
            va="top",
            ha="left",
        )
    ax.set_xlabel("Cognitive complexity", color=INK_SOFT, fontsize=10)
    ax.set_ylabel("Functions", color=INK_SOFT, fontsize=10)
    ax.set_xlim(left=-0.5)
    ax.set_title(
        title or f"Distribution of cognitive complexity ({s.count} functions)",
        color=INK,
        fontsize=12,
        loc="left",
    )
    fig.tight_layout()
    return fig


def plot_commit(
    values: Sequence[int],
    out: Path | str,
    title: str = "",
) -> None:
    """Plot the histogram of the per-function complexity of one commit.

    Args:
        values: Complexity of every function of the commit (not empty).
        out: Destination PNG file.
        title: Chart title; a default is used when empty.
    """
    _save(commit_figure(values, title=title), out)
