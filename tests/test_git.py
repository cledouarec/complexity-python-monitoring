# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

from datetime import UTC, datetime

import pytest

from complexity_python_monitoring.git import (
    GitError,
    list_commits,
    list_python_blobs,
    read_blobs,
    show_commit,
)


def test_list_commits_returns_chronological_order_with_dates(sample_repo):
    repo, shas = sample_repo
    commits = list_commits(repo, "HEAD")
    assert [c.sha for c in commits] == shas
    assert [c.message for c in commits] == ["c1", "c2", "c3"]
    assert commits[0].committed_at == 1704103200  # 2024-01-01T10:00:00Z
    assert commits[0].date == datetime(2024, 1, 1, 10, tzinfo=UTC)
    assert (
        commits[0].committed_at
        < commits[1].committed_at
        < commits[2].committed_at
    )


def test_list_commits_rejects_unknown_rev(sample_repo):
    repo, _ = sample_repo
    with pytest.raises(GitError):
        list_commits(repo, "no-such-branch")


def test_list_commits_rejects_non_repository(tmp_path):
    with pytest.raises(GitError):
        list_commits(tmp_path, "HEAD")


def test_list_python_blobs_only_returns_py_files(sample_repo):
    repo, shas = sample_repo
    blobs = list_python_blobs(repo, shas[2])
    assert sorted(b.path for b in blobs) == ["a.py", "b.py", "tests/bad.py"]
    assert all(len(b.blob_sha) == 40 for b in blobs)


def test_unchanged_file_keeps_same_blob_sha_across_commits(sample_repo):
    repo, shas = sample_repo
    b2 = {b.path: b.blob_sha for b in list_python_blobs(repo, shas[1])}
    b3 = {b.path: b.blob_sha for b in list_python_blobs(repo, shas[2])}
    assert b2["b.py"] == b3["b.py"]
    assert b2["a.py"] != b3["a.py"]


def test_read_blobs_returns_content_by_sha(sample_repo):
    repo, shas = sample_repo
    blobs = {b.path: b.blob_sha for b in list_python_blobs(repo, shas[0])}
    contents = read_blobs(repo, [blobs["a.py"]])
    assert contents[blobs["a.py"]] == "def simple(x):\n    return x\n"


def test_show_commit_expands_prefix_to_full_commit(sample_repo):
    repo, shas = sample_repo
    commit = show_commit(repo, shas[1][:7])
    assert commit.sha == shas[1]
    assert commit.message == "c2"
    assert commit.committed_at == 1706781600  # 2024-02-01T10:00:00Z


def test_show_commit_rejects_unknown_rev(sample_repo):
    repo, _ = sample_repo
    with pytest.raises(GitError):
        show_commit(repo, "deadbeef")
