# Complexity Python Monitoring

## Overview

Track how the [cognitive complexity](https://www.sonarsource.com/resources/cognitive-complexity/)
of a Python code base evolves across its Git history.

For every commit, each function of each `.py` file is scored with
[complexipy](https://github.com/rohaquinlop/complexipy). Results are stored in a
SQLite file and rendered as:

- a **trend chart**: minimum, 1st decile (P10), median, mean, 9th decile (P90)
  and maximum of the per-function complexity, commit after commit;
- a **commit chart**: the full distribution (histogram) of one commit, with the
  most complex functions listed in the terminal.

File contents are cached by Git blob SHA, so a file that does not change between
two commits is analysed once. With `--db`, the analysis is kept in a SQLite file
and re-running `trend` only processes new commits.

## Installation

The package can be installed from the repository with
[uv](https://docs.astral.sh/uv/):

```bash
uv add git+https://github.com/cledouarec/complexity-python-monitoring
```

or run it without installing:

```bash
uvx --from git+https://github.com/cledouarec/complexity-python-monitoring complexity-python-monitoring --help
```

## Usage

### Plot the trend of a repository

```bash
complexity-python-monitoring trend /path/to/repo --out trend.png
```

Analyses every commit of the history and produces `trend.png` (mean and median
lines, P10/P90 lines with the band between them, min/max dotted lines).

Options:

| Option | Description |
| --- | --- |
| `--out FILE` | Output PNG (default `trend.png`). |
| `--rev REV` | Branch, tag or commit to walk (default `HEAD`). The first-parent history is used. |
| `--max-commits N` | Only analyse the `N` most recent commits. |
| `--exclude GLOB` | Skip files whose repository path matches `GLOB` (repeatable, e.g. `--exclude 'tests/*'`). |
| `--db FILE` | Keep the analysis in a SQLite file. A later run on the same file only processes new commits. |
| `--max` / `--no-max` | Draw the max line (default `--max`). `--no-max` leaves it out, so a few outliers do not squash the other lines, and scales the chart to P90. |
| `--title TEXT` | Chart title. |

Without `--db`, the analysis lives in memory and is discarded after the chart is
written.

### Inspect one commit

```bash
complexity-python-monitoring commit /path/to/repo 9c224ff --top 10
```

Accepts a full SHA, a unique prefix, a branch or a tag. Analyses only that
commit, writes `commit-<sha>.png` (histogram of the per-function complexity,
mean and P90 marked) and prints the summary, the `--top` most complex functions
with their file and line, and the files complexipy could not parse. `--exclude`
and `--title` work as for `trend`.

```text
9c224ff docs(readme): add Ukrainian language link to language switcher
228 functions: mean 5.46, median 2.0, min 0, P10 0.0, P90 19.3, max 41 -> commit-9c224ff.png

Top 3 most complex functions:
  41  03-skills/refactor/scripts/detect-smells.py:220  SmellDetector::_detect_long_parameter_lists
  30  03-skills/refactor/scripts/detect-smells.py:391  SmellDetector::_detect_deeply_nested
  30  03-skills/refactor/scripts/detect-smells.py:605  analyze_directory
```

## Contribution

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution guidelines.
