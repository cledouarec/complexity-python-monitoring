# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

import pytest

from complexity_python_monitoring.analyzer import FunctionComplexity
from complexity_python_monitoring.git import BlobRef, Commit
from complexity_python_monitoring.store import Store


@pytest.fixture
def store(tmp_path):
    with Store.open(tmp_path / "db.sqlite") as s:
        yield s


def test_blob_cache_round_trip(store):
    assert not store.has_blob("a" * 40)
    store.save_blob(
        "a" * 40,
        [FunctionComplexity("f", 3, 1), FunctionComplexity("g", 0, 5)],
    )
    store.save_blob("b" * 40, None)  # unparsable
    assert store.has_blob("a" * 40)
    assert store.has_blob("b" * 40)


def test_commit_complexities_join_files_and_functions(store):
    store.save_blob(
        "a" * 40,
        [FunctionComplexity("f", 3, 1), FunctionComplexity("g", 0, 5)],
    )
    store.save_blob("b" * 40, [FunctionComplexity("h", 6, 1)])
    store.save_blob("c" * 40, None)
    store.save_commit(
        Commit("1" * 40, 1700000000, "first"),
        position=0,
        files=[
            BlobRef("a.py", "a" * 40),
            BlobRef("b.py", "b" * 40),
            BlobRef("bad.py", "c" * 40),
        ],
    )
    assert sorted(store.commit_complexities("1" * 40)) == [0, 3, 6]
    assert store.has_commit("1" * 40)
    assert not store.has_commit("2" * 40)


def test_iter_commits_in_position_order(store):
    store.save_commit(
        Commit("2" * 40, 1700000100, "second"),
        position=1,
        files=[],
    )
    store.save_commit(
        Commit("1" * 40, 1700000000, "first"),
        position=0,
        files=[],
    )
    assert [c.message for c in store.iter_commits()] == ["first", "second"]


def test_top_functions_reports_path_and_line(store):
    store.save_blob(
        "a" * 40,
        [FunctionComplexity("f", 3, 1), FunctionComplexity("g", 9, 5)],
    )
    store.save_blob("b" * 40, [FunctionComplexity("h", 6, 1)])
    store.save_commit(
        Commit("1" * 40, 1700000000, "first"),
        position=0,
        files=[BlobRef("pkg/a.py", "a" * 40), BlobRef("b.py", "b" * 40)],
    )
    top = store.top_functions("1" * 40, limit=2)
    assert [(t.path, t.name, t.complexity, t.line_start) for t in top] == [
        ("pkg/a.py", "g", 9, 5),
        ("b.py", "h", 6, 1),
    ]


def test_unparsable_blobs_are_counted_per_commit(store):
    store.save_blob("a" * 40, [FunctionComplexity("f", 3, 1)])
    store.save_blob("c" * 40, None)
    store.save_commit(
        Commit("1" * 40, 1, "x"),
        position=0,
        files=[BlobRef("a.py", "a" * 40), BlobRef("bad.py", "c" * 40)],
    )
    assert store.unparsable_files("1" * 40) == ["bad.py"]
