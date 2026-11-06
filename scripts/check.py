"""Run every quality gate of AGENTS.md section 14 in order, stopping at the first failure.

Usage: ``uv run python scripts/check.py``.
"""

import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[1]


@dataclass(frozen=True, slots=True)
class Gate:
    """One gate: a display name and the command that runs it."""

    name: str
    command: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GateOutcome:
    """Result of one gate: exit code (``None`` when not run) and duration."""

    gate: Gate
    exit_code: int | None
    seconds: float


GATES: Final = (
    Gate("ruff format", ("uv", "run", "ruff", "format")),
    Gate("ruff check", ("uv", "run", "ruff", "check")),
    Gate("basedpyright", ("uv", "run", "basedpyright")),
    Gate("furryp", ("furryp", "check", "concentrator")),
    Gate("pytest", ("uv", "run", "pytest", "--cov", "--cov-report=term-missing", "--cov-report=json")),
    Gate("coverage gate", ("uv", "run", "python", "scripts/coverage_gate.py")),
)
COMMAND_NOT_FOUND: Final = 127


def run_gate(gate: Gate) -> GateOutcome:
    """Run one gate from the repository root, streaming its output.

    Args:
        gate: Gate to run.

    Returns:
        Its outcome; a missing executable counts as a failure.
    """
    print(f"\n=== {gate.name}: {' '.join(gate.command)}", flush=True)
    start = time.perf_counter()
    try:
        completed = subprocess.run(gate.command, cwd=REPO_ROOT, check=False)
    except FileNotFoundError:
        print(f"Command not found: {gate.command[0]} (is it installed and on PATH?)")
        return GateOutcome(gate, COMMAND_NOT_FOUND, time.perf_counter() - start)
    return GateOutcome(gate, completed.returncode, time.perf_counter() - start)


def run_gates(gates: tuple[Gate, ...]) -> list[GateOutcome]:
    """Run the gates in order until one fails; the remaining ones are reported as not run.

    Args:
        gates: Gates to run.

    Returns:
        One outcome per gate.
    """
    outcomes: list[GateOutcome] = []
    for gate in gates:
        if outcomes and outcomes[-1].exit_code != 0:
            outcomes.append(GateOutcome(gate, None, 0.0))
            continue
        outcomes.append(run_gate(gate))
    return outcomes


def print_summary(outcomes: list[GateOutcome]) -> None:
    """Print one line per gate.

    Args:
        outcomes: Outcomes to print.
    """
    print("\n=== Summary")
    for outcome in outcomes:
        if outcome.exit_code is None:
            status = "not run"
        elif outcome.exit_code == 0:
            status = "passed"
        else:
            status = f"FAILED ({outcome.exit_code})"
        print(f"{outcome.gate.name:<14} {status:<14} {outcome.seconds:7.1f} s")


def main() -> int:
    """Run the gates and print the summary.

    Returns:
        0 when every gate passed, 1 otherwise.
    """
    outcomes = run_gates(GATES)
    print_summary(outcomes)
    return 0 if all(outcome.exit_code == 0 for outcome in outcomes) else 1


if __name__ == "__main__":
    sys.exit(main())
