from pathlib import Path
from typing import Final

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from tests.architecture.source_tree import REPO_ROOT

TESTS_ROOT: Final = REPO_ROOT / "tests"
NOT_PRODUCED: Final = frozenset({ErrorCodeEnum.UNKNOWN, ErrorCodeEnum.UNSET})


def _test_sources() -> str:
    paths = (path for path in TESTS_ROOT.rglob("test_*.py") if "__pycache__" not in path.parts)
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(paths) if path != Path(__file__))


def test_every_error_code_appears_in_a_test() -> None:
    sources = _test_sources()

    untested = [
        member.name
        for member in ErrorCodeEnum
        if member not in NOT_PRODUCED and f"ErrorCodeEnum.{member.name}" not in sources
    ]

    assert untested == []
