# Copyright 2026 Christophe Le Douarec
from __future__ import annotations

from click.testing import CliRunner

from complexity_python_monitoring import __version__
from complexity_python_monitoring.cli import main
from complexity_python_monitoring.store import Store


def test_version():
    result = CliRunner().invoke(main, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.output


def test_trend_analyses_repository_and_keeps_database(sample_repo, tmp_path):
    repo, shas = sample_repo
    db = tmp_path / "res.sqlite"
    trend_png = tmp_path / "trend.png"
    runner = CliRunner()

    r = runner.invoke(
        main,
        ["trend", str(repo), "--out", str(trend_png), "--db", str(db)],
    )
    assert r.exit_code == 0, r.output
    assert "3 commits analysed" in r.output
    assert trend_png.stat().st_size > 0
    with Store.open(db) as store:
        assert [c.sha for c in store.iter_commits()] == shas
    assert "mean 0.00 -> 4.50" in r.output
    assert "median" in r.output
    assert "min" in r.output
    assert "max" in r.output

    # A second run on the same database only pays for new commits.
    r = runner.invoke(
        main,
        ["trend", str(repo), "--out", str(trend_png), "--db", str(db)],
    )
    assert r.exit_code == 0, r.output
    assert "0 commits analysed, 3 already known" in r.output


def test_trend_works_without_database(sample_repo, tmp_path):
    repo, _ = sample_repo
    out = tmp_path / "trend.png"
    r = CliRunner().invoke(main, ["trend", str(repo), "--out", str(out)])
    assert r.exit_code == 0, r.output
    assert out.stat().st_size > 0
    assert not list(tmp_path.glob("*.sqlite"))


def test_trend_accepts_no_max(sample_repo, tmp_path):
    repo, _ = sample_repo
    out = tmp_path / "trend.png"
    r = CliRunner().invoke(
        main,
        ["trend", str(repo), "--out", str(out), "--no-max"],
    )
    assert r.exit_code == 0, r.output
    assert out.stat().st_size > 0


def test_trend_respects_max_commits_and_exclude(sample_repo, tmp_path):
    repo, shas = sample_repo
    out, db = tmp_path / "trend.png", tmp_path / "res.sqlite"
    r = CliRunner().invoke(
        main,
        [
            "trend",
            str(repo),
            "--out",
            str(out),
            "--db",
            str(db),
            "--max-commits",
            "2",
            "--exclude",
            "tests/*",
        ],
    )
    assert r.exit_code == 0, r.output
    with Store.open(db) as store:
        assert [c.sha for c in store.iter_commits()] == shas[1:]
    assert "0 unparsable" in r.output


def test_commit_analyses_one_commit(sample_repo, tmp_path):
    repo, shas = sample_repo
    out = tmp_path / "c.png"
    r = CliRunner().invoke(
        main,
        [
            "commit",
            str(repo),
            shas[2][:7],
            "--out",
            str(out),
            "--top",
            "1",
        ],
    )
    assert r.exit_code == 0, r.output
    assert out.stat().st_size > 0
    assert shas[2][:7] in r.output
    assert "min " in r.output
    assert "b.py" in r.output
    assert "branchy" in r.output
    assert "nested" not in r.output
    assert "tests/bad.py" in r.output


def test_trend_rejects_non_repository(tmp_path):
    r = CliRunner().invoke(
        main,
        ["trend", str(tmp_path), "--out", str(tmp_path / "t.png")],
    )
    assert r.exit_code == 2
    assert "git" in r.output.lower()


def test_commit_unknown_sha_fails_cleanly(sample_repo, tmp_path):
    repo, _ = sample_repo
    r = CliRunner().invoke(
        main,
        ["commit", str(repo), "deadbeef", "--out", str(tmp_path / "c.png")],
    )
    assert r.exit_code == 2
    assert "deadbeef" in r.output
