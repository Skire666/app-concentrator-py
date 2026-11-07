"""The ADR-027 recovery matrix: main x tmp x bak (valid / invalid / absent)."""

import itertools
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from concentrator.application.storage.recovery_report import FileProbe
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.startup_plan import RecoveryCandidate, StartupPlan, classify
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from tests.fakes.fake_user_data_file import absent, invalid, report, valid
from tests.fakes.user_data_factory import SAVED_AT, make_stored

PATH = Path("C:/data/concentrator.toml")
DEFAULT = Path("C:/Users/me/AppData/Roaming/Concentrator/concentrator.toml")
MAIN_AT = SAVED_AT
TMP_AT = SAVED_AT + timedelta(seconds=10)
BAK_AT = SAVED_AT - timedelta(seconds=10)
STATES = ("valid", "invalid", "absent")

TMP = RecoveryCandidate(RecoverySourceEnum.TEMPORARY, TMP_AT)
BAK = RecoveryCandidate(RecoverySourceEnum.BACKUP, BAK_AT)


def _probe(state: str, saved_at: datetime) -> FileProbe:
    if state == "valid":
        return valid(make_stored(saved_at=saved_at))
    return invalid() if state == "invalid" else absent()


def _expected(
    main: str, tmp: str, bak: str
) -> tuple[StartupStepEnum, StartupReasonEnum, tuple[RecoveryCandidate, ...]]:
    candidates = tuple(item for item, state in ((TMP, tmp), (BAK, bak)) if state == "valid")
    if main == "valid":
        if tmp == "valid":
            return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.NEWER_TEMPORARY, (TMP,)
        return StartupStepEnum.READY, StartupReasonEnum.OPENED, ()
    if main == "invalid":
        return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.FILE_DAMAGED, candidates
    if candidates:
        return StartupStepEnum.NEEDS_RECOVERY, StartupReasonEnum.FILE_MISSING, candidates
    return StartupStepEnum.NEEDS_LOCATION, StartupReasonEnum.FILE_NOT_FOUND, ()


@pytest.mark.parametrize(("main", "tmp", "bak"), list(itertools.product(STATES, repeat=3)))
def test_recovery_matrix(main: str, tmp: str, bak: str) -> None:
    inspected = report(PATH, _probe(main, MAIN_AT), _probe(tmp, TMP_AT), _probe(bak, BAK_AT))

    plan = classify(inspected, default_path=DEFAULT, default_exists=False)

    assert (plan.step, plan.reason, plan.candidates) == _expected(main, tmp, bak)
    assert plan.path == PATH
    assert plan.problem.is_failure is (main != "valid")


def _plan(main: FileProbe, tmp: FileProbe | None = None, bak: FileProbe | None = None) -> StartupPlan:
    return classify(report(PATH, main, tmp, bak), default_path=DEFAULT, default_exists=True)


def test_tmp_older_than_main_is_ignored() -> None:
    plan = _plan(valid(make_stored(saved_at=MAIN_AT)), valid(make_stored(saved_at=BAK_AT)))

    assert plan.step is StartupStepEnum.READY
    assert plan.candidates == ()
    assert plan.default_exists


def test_tmp_saved_at_the_same_second_as_main_is_ignored() -> None:
    assert (
        _plan(valid(make_stored(saved_at=MAIN_AT)), valid(make_stored(saved_at=MAIN_AT))).step is StartupStepEnum.READY
    )


def test_candidates_are_newest_first_and_tmp_first_on_a_tie() -> None:
    newer_bak = _plan(invalid(), valid(make_stored(saved_at=BAK_AT)), valid(make_stored(saved_at=TMP_AT)))
    tie = _plan(absent(), valid(make_stored(saved_at=MAIN_AT)), valid(make_stored(saved_at=MAIN_AT)))

    assert [item.source for item in newer_bak.candidates] == [RecoverySourceEnum.BACKUP, RecoverySourceEnum.TEMPORARY]
    assert [item.source for item in tie.candidates] == [RecoverySourceEnum.TEMPORARY, RecoverySourceEnum.BACKUP]


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        (ErrorCodeEnum.STORAGE_FILE_UNREADABLE, StartupReasonEnum.FILE_UNREADABLE),
        (ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED, StartupReasonEnum.NEWER_VERSION),
    ],
)
def test_locked_or_newer_file_is_fatal_and_offers_no_candidate(code: ErrorCodeEnum, reason: StartupReasonEnum) -> None:
    plan = _plan(invalid(code), valid(make_stored(saved_at=TMP_AT)), valid(make_stored(saved_at=BAK_AT)))

    assert plan.step is StartupStepEnum.FATAL
    assert plan.reason is reason
    assert plan.candidates == ()
    assert plan.problem.error_codes == (code,)
    assert not plan.can_start_empty
    assert plan.can_choose_another


@pytest.mark.parametrize(
    ("reason", "retry", "keep", "empty", "another"),
    [
        (StartupReasonEnum.FIRST_RUN, False, False, False, False),
        (StartupReasonEnum.FILE_NOT_FOUND, True, False, False, False),
        (StartupReasonEnum.NEWER_TEMPORARY, False, True, False, False),
        (StartupReasonEnum.FILE_DAMAGED, False, False, True, True),
        (StartupReasonEnum.FILE_MISSING, True, False, True, True),
        (StartupReasonEnum.FILE_UNREADABLE, True, False, False, True),
        (StartupReasonEnum.NEWER_VERSION, False, False, False, True),
    ],
)
def test_actions_offered_per_reason(
    reason: StartupReasonEnum, retry: bool, keep: bool, empty: bool, another: bool
) -> None:
    plan = StartupPlan(
        step=StartupStepEnum.NEEDS_RECOVERY, reason=reason, path=PATH, default_path=DEFAULT, default_exists=False
    )

    assert (plan.can_retry, plan.can_keep_current, plan.can_start_empty, plan.can_choose_another) == (
        retry,
        keep,
        empty,
        another,
    )


def test_report_probe_of_each_source() -> None:
    temporary = valid(make_stored(saved_at=TMP_AT))
    backup = invalid()
    inspected = report(PATH, absent(), temporary, backup)

    assert inspected.probe_of(RecoverySourceEnum.TEMPORARY) is temporary
    assert inspected.probe_of(RecoverySourceEnum.BACKUP) is backup
    assert inspected.probe_of(RecoverySourceEnum.UNSET) is None
    assert inspected.main.saved_at is None
    assert temporary.saved_at == TMP_AT
