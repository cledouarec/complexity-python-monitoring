# Copyright 2026 Christophe Le Douarec
"""Thin wrapper around the ``git`` command line (history and blobs)."""

from __future__ import annotations

import shutil
import subprocess  # ruff: ignore[suspicious-subprocess-import] - git is only ever invoked with fixed arguments
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterable
    from pathlib import Path

_BATCH_HEADER_FIELDS = 3  # "<sha> <type> <size>" in ``cat-file --batch``


class GitError(RuntimeError):
    """Raised when git cannot fulfil a request (bad path, unknown rev...)."""


@dataclass(frozen=True)
class Commit:
    """One commit of the walked history."""

    sha: str
    committed_at: int
    message: str

    @property
    def date(self) -> datetime:
        """The commit time as an aware UTC ``datetime``."""
        return datetime.fromtimestamp(self.committed_at, tz=UTC)


@dataclass(frozen=True)
class BlobRef:
    """A file of a given commit, identified by the SHA of its content."""

    path: str
    blob_sha: str


@cache
def _git_executable() -> str:
    """Return the absolute path of the ``git`` executable.

    Raises:
        GitError: If ``git`` is not on the PATH.
    """
    path = shutil.which("git")
    if path is None:  # pragma: no cover - git missing
        message = "git executable not found"
        raise GitError(message)
    return path


def _run(repo: Path, *args: str, stdin: bytes | None = None) -> bytes:
    result = subprocess.run(  # ruff: ignore[subprocess-without-shell-equals-true] - arguments are never user-shell input
        [_git_executable(), "-C", str(repo), *args],
        input=stdin,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        detail = result.stderr.decode("utf-8", "replace").strip()
        message = f"git {' '.join(args)} failed: {detail}"
        raise GitError(message)
    return result.stdout


_LOG_FORMAT = "--format=%H%x00%ct%x00%s"


def _parse_log(out: bytes) -> list[Commit]:
    commits = []
    for line in out.decode("utf-8", "replace").splitlines():
        if not line:
            continue
        sha, ts, message = line.split("\x00", 2)
        commits.append(Commit(sha=sha, committed_at=int(ts), message=message))
    return commits


def list_commits(repo: Path, rev: str = "HEAD") -> list[Commit]:
    """Return the first-parent history of ``rev``, oldest commit first.

    Args:
        repo: Path to the working tree or ``.git`` directory.
        rev: Branch, tag or commit to walk backwards from.

    Returns:
        The commits reachable from ``rev`` along first parents, oldest first.
    """
    out = _run(
        repo,
        "log",
        "--first-parent",
        "--reverse",
        _LOG_FORMAT,
        rev,
        "--",
    )
    return _parse_log(out)


def show_commit(repo: Path, rev: str) -> Commit:
    """Resolve ``rev`` (full SHA, prefix, branch, tag...) to one commit.

    Args:
        repo: Path to the working tree or ``.git`` directory.
        rev: Anything ``git log`` accepts as a single revision.

    Returns:
        The commit ``rev`` points at, with its full SHA.

    Raises:
        GitError: If ``repo`` is not a repository or ``rev`` is unknown.
    """
    out = _run(repo, "log", "-1", _LOG_FORMAT, rev, "--")
    commits = _parse_log(out)
    if not commits:
        message = f"no commit matches '{rev}'"
        raise GitError(message)
    return commits[0]


def list_python_blobs(repo: Path, commit_sha: str) -> list[BlobRef]:
    """List the ``.py`` files present in ``commit_sha`` with their blob SHA.

    Args:
        repo: Path to the repository.
        commit_sha: Full SHA of the commit to inspect.

    Returns:
        One entry per Python file of the commit tree.
    """
    out = _run(repo, "ls-tree", "-r", "-z", commit_sha)
    blobs = []
    for entry in out.split(b"\x00"):
        if not entry:
            continue
        meta, path = entry.split(b"\t", 1)
        _mode, kind, sha = meta.split(b" ")
        if kind != b"blob":
            continue
        name = path.decode("utf-8", "surrogateescape")
        if name.endswith(".py"):
            blobs.append(BlobRef(path=name, blob_sha=sha.decode()))
    return blobs


def read_blobs(repo: Path, blob_shas: Iterable[str]) -> dict[str, str]:
    """Read several blobs in one ``git cat-file --batch`` round trip.

    Contents are decoded as UTF-8 with replacement so a stray byte never
    aborts the analysis of a whole commit.

    Args:
        repo: Path to the repository.
        blob_shas: SHAs of the blobs to read.

    Returns:
        The decoded content of each blob, keyed by SHA. Missing blobs are
        silently absent from the result.
    """
    shas = list(blob_shas)
    if not shas:
        return {}
    stdin = "".join(f"{sha}\n" for sha in shas).encode()
    out = _run(repo, "cat-file", "--batch", stdin=stdin)
    contents: dict[str, str] = {}
    pos = 0
    while pos < len(out):
        nl = out.index(b"\n", pos)
        header = out[pos:nl].decode()
        pos = nl + 1
        parts = header.split(" ")
        if len(parts) != _BATCH_HEADER_FIELDS:  # "<sha> missing"
            continue
        sha, _kind, size = parts
        length = int(size)
        contents[sha] = out[pos : pos + length].decode("utf-8", "replace")
        pos += length + 1  # trailing newline after each object
    return contents
