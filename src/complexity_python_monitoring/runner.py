# Copyright 2026 Christophe Le Douarec
"""Orchestrates git history reading, complexity analysis and persistence."""

from __future__ import annotations

from contextlib import nullcontext
from dataclasses import dataclass, fields
from fnmatch import fnmatch
from typing import TYPE_CHECKING

from . import analyzer
from .git import list_commits, list_python_blobs, read_blobs
from .stats import TrendPoint, summarize

if TYPE_CHECKING:
    from collections.abc import Callable, Iterable, Sequence
    from contextlib import AbstractContextManager
    from pathlib import Path

    from .git import BlobRef, Commit
    from .store import Store

type Progress = Callable[
    [Sequence[Commit]],
    AbstractContextManager[Iterable[Commit]],
]
"""Wraps the commits to analyse (e.g. in a progress bar) before iteration."""


@dataclass(frozen=True)
class Report:
    """Counters describing one analysis run."""

    commits_analyzed: int = 0
    commits_skipped: int = 0
    blobs_analyzed: int = 0
    blobs_unparsable: int = 0

    def __add__(self, other: Report) -> Report:
        """Add the counters of two runs.

        Returns:
            A new report where every counter is the sum of both.
        """
        return Report(
            **{
                f.name: getattr(self, f.name) + getattr(other, f.name)
                for f in fields(self)
            },
        )


def _keep(blob: BlobRef, exclude: Sequence[str]) -> bool:
    return not any(fnmatch(blob.path, pattern) for pattern in exclude)


def analyze_commit(
    repo: Path,
    store: Store,
    commit: Commit,
    position: int = 0,
    exclude: Sequence[str] = (),
) -> Report:
    """Analyse the Python files of one commit and record them.

    Blobs already present in the store are not analysed again.

    Args:
        repo: Path to the Git repository.
        store: Where results are written.
        commit: The commit to analyse.
        position: Index of the commit in the walked history.
        exclude: Glob patterns of repository paths to skip.

    Returns:
        Counters of what was analysed and unparsable.
    """
    files = [
        b for b in list_python_blobs(repo, commit.sha) if _keep(b, exclude)
    ]
    missing = sorted(
        sha for sha in {b.blob_sha for b in files} if not store.has_blob(sha)
    )
    analyses = {
        sha: analyzer.analyze_source(source)
        for sha, source in read_blobs(repo, missing).items()
    }
    for sha, functions in analyses.items():
        store.save_blob(sha, functions)
    store.save_commit(commit, position=position, files=files)
    return Report(
        commits_analyzed=1,
        blobs_analyzed=len(analyses),
        blobs_unparsable=sum(f is None for f in analyses.values()),
    )


def analyze_repository(
    repo: Path,
    store: Store,
    rev: str = "HEAD",
    max_commits: int | None = None,
    exclude: Sequence[str] = (),
    progress: Progress = nullcontext,
) -> Report:
    """Analyse every commit of ``rev`` (first-parent, oldest first).

    Commits already present in the store are skipped, and a blob is analysed
    at most once, so re-running on a grown history only pays for what is new.

    Args:
        repo: Path to the Git repository.
        store: Where results are written.
        rev: Branch, tag or commit whose history is walked.
        max_commits: Only analyse the N most recent commits.
        exclude: Glob patterns of repository paths to skip.
        progress: Wraps the commits about to be walked, typically in a
            progress bar such as ``click.progressbar``.

    Returns:
        Counters of what was analysed, skipped and unparsable.
    """
    history = list_commits(repo, rev)
    first = 0 if max_commits is None else max(0, len(history) - max_commits)
    report = Report()
    with progress(history[first:]) as commits:
        for position, commit in enumerate(commits, start=first):
            if store.has_commit(commit.sha):
                report += Report(commits_skipped=1)
            else:
                report += analyze_commit(
                    repo,
                    store,
                    commit,
                    position,
                    exclude,
                )
    return report


def trend_points(store: Store) -> list[TrendPoint]:
    """Summarise every recorded commit that contains at least one function.

    Args:
        store: Where the analysis was recorded.

    Returns:
        One point per commit, in history order.
    """
    points = []
    for commit in store.iter_commits():
        values = store.commit_complexities(commit.sha)
        if values:
            point = TrendPoint(date=commit.date, summary=summarize(values))
            points.append(point)
    return points
