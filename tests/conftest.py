# Copyright 2026 Christophe Le Douarec
"""Shared fixtures: a small temporary Git repository with a known history."""

from __future__ import annotations

import shutil
import subprocess
from typing import TYPE_CHECKING

import pytest

from tests.samples import BRANCHY, INVALID, NESTED, SIMPLE

if TYPE_CHECKING:
    from pathlib import Path


def git(repo: Path, *args: str, date: str | None = None) -> str:
    env = {
        "GIT_AUTHOR_NAME": "Test",
        "GIT_AUTHOR_EMAIL": "test@example.com",
        "GIT_COMMITTER_NAME": "Test",
        "GIT_COMMITTER_EMAIL": "test@example.com",
        "HOME": str(repo),
        "PATH": "/usr/bin:/bin",
    }
    if date:
        env["GIT_AUTHOR_DATE"] = date
        env["GIT_COMMITTER_DATE"] = date
    return subprocess.run(
        [shutil.which("git") or "git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    ).stdout.strip()


def commit_files(
    repo: Path,
    files: dict[str, str],
    message: str,
    date: str,
) -> str:
    for name, content in files.items():
        path = repo / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", message, date=date)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def sample_repo(tmp_path: Path) -> tuple[Path, list[str]]:
    """Build a repository with three linear commits.

    c1: a.py (simple)                        -> complexities [0]
    c2: a.py (simple), b.py (branchy)        -> complexities [0, 6]
    c3: a.py (nested), b.py (branchy),
        tests/bad.py (invalid), notes.txt    -> [3, 6], one bad blob

    Returns:
        The repository path and the three commit SHAs, oldest first.
    """
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    shas = [
        commit_files(
            repo,
            {"a.py": SIMPLE},
            "c1",
            "2024-01-01T10:00:00+00:00",
        ),
        commit_files(
            repo,
            {"b.py": BRANCHY},
            "c2",
            "2024-02-01T10:00:00+00:00",
        ),
        commit_files(
            repo,
            {"a.py": NESTED, "tests/bad.py": INVALID, "notes.txt": "hello\n"},
            "c3",
            "2024-03-01T10:00:00+00:00",
        ),
    ]
    return repo, shas
