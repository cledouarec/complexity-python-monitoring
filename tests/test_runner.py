# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

from contextlib import nullcontext

from complexity_python_monitoring import analyzer
from complexity_python_monitoring.git import show_commit
from complexity_python_monitoring.runner import (
    analyze_commit,
    analyze_repository,
    trend_points,
)
from complexity_python_monitoring.store import Store


def test_analyze_repository_records_every_commit(sample_repo, tmp_path):
    repo, shas = sample_repo
    with Store.open(tmp_path / "db.sqlite") as store:
        report = analyze_repository(repo, store)
        assert report.commits_analyzed == 3
        assert report.blobs_analyzed == 4  # a.py v1, b.py, a.py v2, bad.py
        assert report.blobs_unparsable == 1
        assert sorted(store.commit_complexities(shas[0])) == [0]
        assert sorted(store.commit_complexities(shas[1])) == [0, 6]
        assert sorted(store.commit_complexities(shas[2])) == [3, 6]
        assert store.unparsable_files(shas[2]) == ["tests/bad.py"]


def test_analyze_repository_is_incremental(sample_repo, tmp_path, monkeypatch):
    repo, _ = sample_repo
    with Store.open(tmp_path / "db.sqlite") as store:
        analyze_repository(repo, store)
        calls = []
        monkeypatch.setattr(
            analyzer,
            "analyze_source",
            lambda src: calls.append(src) or analyzer.analyze_source(src),
        )
        report = analyze_repository(repo, store)
    assert report.commits_analyzed == 0
    assert calls == []


def test_analyze_repository_respects_max_commits_and_exclude(
    sample_repo,
    tmp_path,
):
    repo, shas = sample_repo
    with Store.open(tmp_path / "db.sqlite") as store:
        report = analyze_repository(
            repo,
            store,
            max_commits=2,
            exclude=("tests/*",),
        )
        assert report.commits_analyzed == 2
        assert not store.has_commit(shas[0])
        assert store.unparsable_files(shas[2]) == []
        assert sorted(store.commit_complexities(shas[2])) == [3, 6]


def test_analyze_repository_hands_walked_commits_to_progress(
    sample_repo,
    tmp_path,
):
    repo, shas = sample_repo
    seen = []

    def spy(commits):
        seen.extend(c.sha for c in commits)
        return nullcontext(commits)

    with Store.open(tmp_path / "db.sqlite") as store:
        analyze_repository(repo, store, max_commits=2, progress=spy)
    assert seen == shas[1:]


def test_trend_points_summarise_commits_with_functions_in_order(
    sample_repo,
    tmp_path,
):
    repo, _ = sample_repo
    with Store.open(tmp_path / "db.sqlite") as store:
        analyze_repository(repo, store)
        points = trend_points(store)
    assert [p.summary.count for p in points] == [1, 2, 2]
    assert [p.summary.mean for p in points] == [0, 3, 4.5]
    assert points[0].date < points[1].date < points[2].date


def test_analyze_commit_records_only_that_commit(sample_repo):
    repo, shas = sample_repo
    with Store.open(":memory:") as store:
        report = analyze_commit(repo, store, show_commit(repo, shas[2]))
        assert report.commits_analyzed == 1
        assert report.blobs_analyzed == 3
        assert report.blobs_unparsable == 1
        assert [c.sha for c in store.iter_commits()] == [shas[2]]
        assert sorted(store.commit_complexities(shas[2])) == [3, 6]
        assert store.unparsable_files(shas[2]) == ["tests/bad.py"]


def test_analyze_commit_honours_exclude(sample_repo):
    repo, shas = sample_repo
    with Store.open(":memory:") as store:
        analyze_commit(
            repo,
            store,
            show_commit(repo, shas[2]),
            exclude=("tests/*",),
        )
        assert store.unparsable_files(shas[2]) == []
