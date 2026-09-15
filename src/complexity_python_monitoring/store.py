# Copyright 2026 Christophe Le Douarec
"""SQLite persistence: commits, their files, and per-blob complexities.

The blob table is the cache: a blob SHA identifies file content, so an
unchanged file shared by hundreds of commits is analysed exactly once.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from itertools import starmap
from typing import TYPE_CHECKING, Self

from .git import Commit

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator
    from pathlib import Path

    from .analyzer import FunctionComplexity
    from .git import BlobRef

_SCHEMA = """
CREATE TABLE IF NOT EXISTS commits (
    sha          TEXT PRIMARY KEY,
    position     INTEGER NOT NULL,
    committed_at INTEGER NOT NULL,
    message      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS commit_files (
    commit_sha TEXT NOT NULL,
    path       TEXT NOT NULL,
    blob_sha   TEXT NOT NULL,
    PRIMARY KEY (commit_sha, path)
);
CREATE INDEX IF NOT EXISTS commit_files_blob ON commit_files (blob_sha);
CREATE TABLE IF NOT EXISTS blobs (
    sha TEXT PRIMARY KEY,
    ok  INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS functions (
    blob_sha   TEXT NOT NULL,
    name       TEXT NOT NULL,
    complexity INTEGER NOT NULL,
    line_start INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS functions_blob ON functions (blob_sha);
"""


@dataclass(frozen=True)
class TopFunction:
    """A function of a commit, located by file path and line."""

    path: str
    name: str
    complexity: int
    line_start: int


class Store:
    """Persistent analysis results backed by one SQLite file."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        """Wrap an open connection; prefer :meth:`open`."""
        self._conn = conn

    @classmethod
    def open(cls, path: Path | str) -> Self:
        """Open (and create if needed) the database at ``path``.

        Args:
            path: SQLite file location.

        Returns:
            A store ready for use, with the schema in place.
        """
        conn = sqlite3.connect(str(path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript(_SCHEMA)
        return cls(conn)

    def close(self) -> None:
        """Close the underlying connection."""
        self._conn.close()

    def __enter__(self) -> Self:
        """Support ``with Store.open(...) as store``.

        Returns:
            The store itself.
        """
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the connection when leaving the ``with`` block."""
        self.close()

    def _exists(self, query: str, *params: object) -> bool:
        return self._conn.execute(query, params).fetchone() is not None

    # --- blobs -----------------------------------------------------------

    def has_blob(self, blob_sha: str) -> bool:
        """Tell whether ``blob_sha`` has already been analysed.

        Returns:
            ``True`` if the blob is in the cache, parsable or not.
        """
        return self._exists("SELECT 1 FROM blobs WHERE sha = ?", blob_sha)

    def save_blob(
        self,
        blob_sha: str,
        functions: Iterable[FunctionComplexity] | None,
    ) -> None:
        """Record the analysis of one blob.

        Args:
            blob_sha: SHA of the file content.
            functions: Its functions, or ``None`` if it could not be parsed.
        """
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO blobs (sha, ok) VALUES (?, ?)",
                (blob_sha, 0 if functions is None else 1),
            )
            self._conn.execute(
                "DELETE FROM functions WHERE blob_sha = ?",
                (blob_sha,),
            )
            if functions is not None:
                self._conn.executemany(
                    "INSERT INTO functions "
                    "(blob_sha, name, complexity, line_start) "
                    "VALUES (?, ?, ?, ?)",
                    [
                        (blob_sha, f.name, f.complexity, f.line_start)
                        for f in functions
                    ],
                )

    # --- commits ---------------------------------------------------------

    def has_commit(self, sha: str) -> bool:
        """Tell whether commit ``sha`` has already been recorded.

        Returns:
            ``True`` if the commit was saved by a previous run.
        """
        return self._exists("SELECT 1 FROM commits WHERE sha = ?", sha)

    def save_commit(
        self,
        commit: Commit,
        position: int,
        files: Iterable[BlobRef],
    ) -> None:
        """Record a commit and the Python files it contains.

        Args:
            commit: The commit metadata.
            position: Index in the walked history, used for ordering.
            files: The Python files of the commit tree.
        """
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO commits "
                "(sha, position, committed_at, message) VALUES (?, ?, ?, ?)",
                (commit.sha, position, commit.committed_at, commit.message),
            )
            self._conn.execute(
                "DELETE FROM commit_files WHERE commit_sha = ?",
                (commit.sha,),
            )
            self._conn.executemany(
                "INSERT INTO commit_files (commit_sha, path, blob_sha) "
                "VALUES (?, ?, ?)",
                [(commit.sha, f.path, f.blob_sha) for f in files],
            )

    def iter_commits(self) -> Iterator[Commit]:
        """Yield the recorded commits in history order."""
        rows = self._conn.execute(
            "SELECT sha, committed_at, message FROM commits ORDER BY position",
        )
        for sha, committed_at, message in rows:
            yield Commit(sha=sha, committed_at=committed_at, message=message)

    # --- queries ---------------------------------------------------------

    def commit_complexities(self, sha: str) -> list[int]:
        """Return the complexity of every function of commit ``sha``."""
        rows = self._conn.execute(
            "SELECT f.complexity FROM commit_files cf "
            "JOIN functions f ON f.blob_sha = cf.blob_sha "
            "WHERE cf.commit_sha = ?",
            (sha,),
        )
        return [r[0] for r in rows]

    def top_functions(self, sha: str, limit: int = 10) -> list[TopFunction]:
        """Return the ``limit`` most complex functions of commit ``sha``."""
        rows = self._conn.execute(
            "SELECT cf.path, f.name, f.complexity, f.line_start "
            "FROM commit_files cf "
            "JOIN functions f ON f.blob_sha = cf.blob_sha "
            "WHERE cf.commit_sha = ? "
            "ORDER BY f.complexity DESC, cf.path, f.line_start LIMIT ?",
            (sha, limit),
        )
        return list(starmap(TopFunction, rows))

    def unparsable_files(self, sha: str) -> list[str]:
        """Return the paths of commit ``sha`` that could not be parsed."""
        rows = self._conn.execute(
            "SELECT cf.path FROM commit_files cf "
            "JOIN blobs b ON b.sha = cf.blob_sha "
            "WHERE cf.commit_sha = ? AND b.ok = 0 ORDER BY cf.path",
            (sha,),
        )
        return [r[0] for r in rows]
