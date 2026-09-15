# Copyright 2026 Christophe Le Douarec
"""Command line interface for Complexity Python Monitoring."""

from __future__ import annotations

import sys
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import click

from . import __version__
from .git import GitError, show_commit
from .plotting import plot_commit, plot_trend
from .runner import analyze_commit, analyze_repository, trend_points
from .stats import summarize
from .store import Store

if TYPE_CHECKING:
    from .runner import Report

REPO_ARGUMENT = click.argument(
    "repo",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
)
EXCLUDE_OPTION = click.option(
    "--exclude",
    multiple=True,
    metavar="GLOB",
    help="Skip files whose path matches GLOB (repeatable, e.g. 'tests/*').",
)
TITLE_OPTION = click.option("--title", default="", help="Chart title.")


def _fail(message: str) -> NoReturn:
    click.secho(f"error: {message}", fg="red", err=True)
    sys.exit(2)


def _report_line(report: Report) -> str:
    return (
        f"{report.commits_analyzed} commits analysed, "
        f"{report.commits_skipped} already known, "
        f"{report.blobs_analyzed} files parsed "
        f"({report.blobs_unparsable} unparsable)"
    )


@click.group()
@click.version_option(__version__, prog_name="complexity-python-monitoring")
def main() -> None:
    """Track the cognitive complexity of a Git repository over time."""


@main.command()
@REPO_ARGUMENT
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default="trend.png",
    show_default=True,
    help="Output PNG.",
)
@click.option(
    "--rev",
    default="HEAD",
    show_default=True,
    help="Branch, tag or commit to walk.",
)
@click.option(
    "--max-commits",
    type=int,
    default=None,
    help="Only the N most recent commits.",
)
@EXCLUDE_OPTION
@click.option(
    "--db",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help=(
        "Keep the analysis in this SQLite file; a later run on the same "
        "file only processes new commits."
    ),
)
@click.option(
    "--max/--no-max",
    "with_max",
    default=True,
    show_default=True,
    help=(
        "Draw the max line. --no-max leaves it out so a few outliers do "
        "not squash the other lines."
    ),
)
@TITLE_OPTION
def trend(  # ruff: ignore[too-many-arguments] - one parameter per CLI option
    *,
    repo: Path,
    out: Path,
    rev: str,
    max_commits: int | None,
    exclude: tuple[str, ...],
    db: Path | None,
    with_max: bool,
    title: str,
) -> None:
    """Analyse the history of REPO and plot the complexity trend."""
    with Store.open(db or ":memory:") as store:
        try:
            report = analyze_repository(
                repo,
                store,
                rev=rev,
                max_commits=max_commits,
                exclude=exclude,
                progress=partial(
                    click.progressbar,
                    label="Analysing commits",
                    show_pos=True,
                ),
            )
        except GitError as exc:
            _fail(str(exc))
        points = trend_points(store)
    click.echo(_report_line(report) + (f" -> {db}" if db else ""))
    if not points:
        _fail("no analysed commits contain Python functions")
    plot_trend(points, out, title=title, with_max=with_max)
    first, last = points[0].summary, points[-1].summary
    click.echo(f"{len(points)} commits plotted -> {out}")
    click.echo(
        f"functions {first.count} -> {last.count}, "
        f"mean {first.mean:.2f} -> {last.mean:.2f}, "
        f"median {first.median:.1f} -> {last.median:.1f}",
    )
    click.echo(
        f"min {first.min} -> {last.min}, "
        f"P10 {first.p10:.1f} -> {last.p10:.1f}, "
        f"P90 {first.p90:.1f} -> {last.p90:.1f}, "
        f"max {first.max} -> {last.max}",
    )


@main.command()
@REPO_ARGUMENT
@click.argument("sha")
@click.option(
    "--out",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output PNG (default: commit-<sha>.png).",
)
@click.option(
    "--top",
    type=int,
    default=10,
    show_default=True,
    help="Number of most complex functions to list.",
)
@EXCLUDE_OPTION
@TITLE_OPTION
def commit(
    *,
    repo: Path,
    sha: str,
    out: Path | None,
    top: int,
    exclude: tuple[str, ...],
    title: str,
) -> None:
    """Analyse one commit of REPO (SHA, prefix, branch or tag) and plot it."""
    try:
        target = show_commit(repo, sha)
    except GitError as exc:
        _fail(str(exc))
    with Store.open(":memory:") as store:
        analyze_commit(repo, store, target, exclude=exclude)
        values = store.commit_complexities(target.sha)
        worst = store.top_functions(target.sha, limit=top)
        bad = store.unparsable_files(target.sha)
    short = target.sha[:7]
    if not values:
        _fail(f"commit {short} contains no Python functions")
    out = out or Path(f"commit-{short}.png")
    s = summarize(values)
    plot_commit(
        values,
        out,
        title=title or f"{short} - {target.message} ({s.count} functions)",
    )
    click.echo(f"{short} {target.message}")
    click.echo(
        f"{s.count} functions: mean {s.mean:.2f}, median {s.median:.1f}, "
        f"min {s.min}, P10 {s.p10:.1f}, P90 {s.p90:.1f}, max {s.max} "
        f"-> {out}",
    )
    if worst:
        click.echo(f"\nTop {len(worst)} most complex functions:")
        width = max(len(str(w.complexity)) for w in worst)
        for w in worst:
            location = f"{w.path}:{w.line_start}"
            click.echo(f"  {w.complexity:>{width}}  {location}  {w.name}")
    if bad:
        click.echo(
            f"\n{len(bad)} file(s) could not be parsed: {', '.join(bad)}",
        )
