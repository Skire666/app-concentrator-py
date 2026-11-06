"""Enforce the per-layer branch coverage thresholds of AGENTS.md section 12.

coverage.py supports a single global ``fail_under``; this script reads ``coverage.json`` (written by
``pytest --cov-report=json``) and checks each layer. Usage: ``uv run python scripts/coverage_gate.py``.
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final, cast

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
REPORT_PATH: Final = REPO_ROOT / "coverage.json"
PERCENT: Final = 100.0


@dataclass(frozen=True, slots=True)
class Scope:
    """A path prefix and its minimum coverage percentage."""

    name: str
    prefix: str
    minimum: float


@dataclass(frozen=True, slots=True)
class Tally:
    """Covered and total measurable units (statements plus branches)."""

    covered: int = 0
    total: int = 0

    def plus(self, covered: int, total: int) -> Tally:
        """Return a tally with more units added."""
        return Tally(self.covered + covered, self.total + total)

    @property
    def percent(self) -> float:
        """Coverage percentage, 100 when there is nothing to measure."""
        return PERCENT if self.total == 0 else PERCENT * self.covered / self.total


SCOPES: Final = (
    Scope("domain", "concentrator/domain/", 90.0),
    Scope("application", "concentrator/application/", 85.0),
    Scope("presentation", "concentrator/presentation/", 80.0),
    Scope("overall", "concentrator/", 75.0),
)
SUMMARY_KEYS: Final = ("covered_lines", "num_statements", "covered_branches", "num_branches")


def load_file_summaries(report_path: Path) -> dict[str, dict[str, int]]:
    """Read the per-file summaries of a coverage JSON report.

    Args:
        report_path: Path of ``coverage.json``.

    Returns:
        File path (POSIX separators) to its summary counters.
    """
    report = cast("dict[str, object]", json.loads(report_path.read_text(encoding="utf-8")))
    files = cast("dict[str, dict[str, dict[str, int]]]", report["files"])
    return {path.replace("\\", "/"): entry["summary"] for path, entry in files.items()}


def tally_scope(summaries: dict[str, dict[str, int]], scope: Scope) -> Tally:
    """Aggregate the files under one prefix.

    Args:
        summaries: Output of ``load_file_summaries``.
        scope: Scope to aggregate.

    Returns:
        The scope tally.
    """
    tally = Tally()
    for path, summary in summaries.items():
        if path.startswith(scope.prefix):
            lines, statements, branches, num_branches = (summary.get(key, 0) for key in SUMMARY_KEYS)
            tally = tally.plus(lines + branches, statements + num_branches)
    return tally


def check_scopes(summaries: dict[str, dict[str, int]]) -> bool:
    """Print one line per scope and tell whether every threshold is met.

    Args:
        summaries: Output of ``load_file_summaries``.

    Returns:
        True when every scope reaches its minimum and the overall scope is not empty.
    """
    passed = True
    print(f"{'scope':<13} {'coverage':>9} {'minimum':>8}  status")
    for scope in SCOPES:
        tally = tally_scope(summaries, scope)
        empty_overall = scope.name == "overall" and tally.total == 0
        ok = tally.percent >= scope.minimum and not empty_overall
        status = "no code yet" if tally.total == 0 else ("ok" if ok else "FAILED")
        print(f"{scope.name:<13} {tally.percent:8.2f}% {scope.minimum:7.1f}%  {status}")
        passed = passed and ok
    return passed


def main() -> int:
    """Check the coverage report.

    Returns:
        0 when every threshold is met, 1 otherwise.
    """
    if not REPORT_PATH.is_file():
        print(f"{REPORT_PATH.name} not found: run pytest with --cov-report=json first.")
        return 1
    return 0 if check_scopes(load_file_summaries(REPORT_PATH)) else 1


if __name__ == "__main__":
    sys.exit(main())
