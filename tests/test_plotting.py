# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

from datetime import UTC, datetime

from complexity_python_monitoring.plotting import (
    commit_figure,
    plot_commit,
    plot_trend,
    trend_figure,
)
from complexity_python_monitoring.stats import TrendPoint, summarize


def _png(path) -> bool:
    return path.exists() and path.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


def _points() -> list[TrendPoint]:
    return [
        TrendPoint(
            date=datetime(2024, i + 1, 1, tzinfo=UTC),
            summary=summarize([i, i + 2, i + 5, i + 9]),
        )
        for i in range(1, 5)
    ]


def test_plot_trend_writes_png(tmp_path):
    out = tmp_path / "trend.png"
    plot_trend(_points(), out, title="demo")
    assert _png(out)


def test_trend_figure_draws_every_summary_measure():
    fig = trend_figure(_points(), title="demo")
    assert len(fig.axes) == 1
    labels = {t.get_text() for t in fig.axes[0].get_legend().get_texts()}
    expected = {"Min", "1st decile", "Median", "Mean", "9th decile", "Max"}
    assert expected <= labels


def test_trend_figure_ceiling_covers_max():
    points = _points()
    fig = trend_figure(points, title="demo")
    top = max(p.summary.max for p in points)
    assert fig.axes[0].get_ylim()[1] >= top


def _legend_labels(ax) -> set[str]:
    return {t.get_text() for t in ax.get_legend().get_texts()}


def test_trend_figure_without_max_drops_the_max_line():
    fig = trend_figure(_points(), title="demo", with_max=False)
    assert len(fig.axes) == 1
    labels = _legend_labels(fig.axes[0])
    assert "Max" not in labels
    assert {"Min", "1st decile", "Median", "Mean", "9th decile"} <= labels


def test_trend_figure_without_max_zooms_below_max():
    points = _points()
    fig = trend_figure(points, title="demo", with_max=False)
    top = max(p.summary.max for p in points)
    p90 = max(p.summary.p90 for p in points)
    upper = fig.axes[0].get_ylim()[1]
    assert p90 <= upper < top


def test_plot_trend_without_max_writes_png(tmp_path):
    out = tmp_path / "trend.png"
    plot_trend(_points(), out, title="demo", with_max=False)
    assert _png(out)


def test_plot_commit_writes_png(tmp_path):
    out = tmp_path / "commit.png"
    plot_commit([0, 0, 1, 2, 2, 3, 6, 15], out, title="abc1234 — demo")
    assert _png(out)


def test_commit_figure_marks_mean_and_p90():
    fig = commit_figure([0, 0, 1, 2, 2, 3, 6, 15])
    labels = {t.get_text().strip() for t in fig.axes[0].texts}
    assert labels == {"mean 3.6", "P90 9"}
    assert "8 functions" in fig.axes[0].get_title(loc="left")
