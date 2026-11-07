from datetime import timedelta

import pytest

from concentrator.application.storage.startup_commands import DATA_FILE_PATH_KEY
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.storage.startup_flow_presenter import StartupFlowPresenter
from concentrator.presentation.storage.startup_snapshots import FirstRunSnapshot, RecoverySnapshot
from tests.fakes.fake_startup_dialogs import FakeStartupDialogs, Step
from tests.fakes.fake_user_data_file import absent, invalid, report, valid
from tests.fakes.storage_stack import DATA_PATH, DEFAULT_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_stored

A = ActionIdEnum
OLDER = SAVED_AT - timedelta(minutes=5)


class Setup:
    def __init__(self) -> None:
        self.stack = StorageStack()
        self.presenter = StartupFlowPresenter(
            commands=self.stack.commands,
            dialogs=self.stack.dialogs,
            gate=self.stack.gate,
            renderer=self.stack.renderer,
            translator=self.stack.translator,
            formatter=self.stack.formatter,
        )
        self.ui = FakeStartupDialogs()
        self.presenter.attach(self.ui)
        self.first_runs: list[FirstRunSnapshot | None] = []
        self.recoveries: list[RecoverySnapshot | None] = []
        self.stack.renderer.register(
            RenderSectionEnum.FIRST_RUN, self.presenter.build_first_run_snapshot, self.first_runs.append
        )
        self.stack.renderer.register(
            RenderSectionEnum.RECOVERY, self.presenter.build_recovery_snapshot, self.recoveries.append
        )
        self.seen_first_run: list[FirstRunSnapshot] = []
        self.seen_recovery: list[RecoverySnapshot] = []

    def script(self, *steps: Step) -> None:
        self.ui.steps.extend(steps)

    def click(self, action: ActionIdEnum) -> Step:
        return lambda: self.stack.click(self.presenter, action)

    def look_first_run(self) -> None:
        snapshot = self.presenter.build_first_run_snapshot()
        assert snapshot is not None
        self.seen_first_run.append(snapshot)

    def look_recovery(self) -> None:
        snapshot = self.presenter.build_recovery_snapshot()
        assert snapshot is not None
        self.seen_recovery.append(snapshot)

    def remember(self) -> None:
        self.stack.preferences.values[DATA_FILE_PATH_KEY] = DATA_PATH.as_posix()


def _visible(buttons: tuple[ButtonSnapshot, ...]) -> list[ActionIdEnum]:
    return [button.action for button in buttons if button.visible]


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_remembered_valid_file_opens_without_dialog(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored()))

    assert setup.presenter.run()
    assert setup.ui.shown == []
    assert setup.presenter.plan is not None
    assert setup.presenter.plan.step is StartupStepEnum.READY
    assert setup.presenter.build_first_run_snapshot() is None
    assert setup.presenter.build_recovery_snapshot() is None


def test_first_run_create_at_the_default_location(setup: Setup) -> None:
    setup.script(setup.look_first_run, setup.click(A.STARTUP_CREATE_DEFAULT_FILE))

    assert setup.presenter.run()

    snapshot = setup.seen_first_run[0]
    assert snapshot.title == "en:startup.first_run.title"
    assert snapshot.intro == "en:startup.first_run.intro"
    assert not snapshot.notice
    assert snapshot.default_location == f"en:startup.first_run.default_location(path={DEFAULT_PATH.as_posix()})"
    assert _visible(snapshot.buttons) == [
        A.STARTUP_CREATE_DEFAULT_FILE,
        A.STARTUP_CREATE_FILE_ELSEWHERE,
        A.STARTUP_OPEN_EXISTING_FILE,
        A.STARTUP_QUIT,
    ]
    assert snapshot.buttons[1].text == "en:action.startup_create_default_file"
    assert setup.ui.shown == ["first_run"]
    assert setup.stack.preferences.get_text(DATA_FILE_PATH_KEY) == DEFAULT_PATH.as_posix()
    assert setup.stack.session.data.settings.language is LanguageEnum.ENGLISH


def test_first_run_uses_the_file_found_at_the_default_location(setup: Setup) -> None:
    setup.stack.file.existing.add(DEFAULT_PATH)
    setup.stack.file.reports[DEFAULT_PATH] = report(DEFAULT_PATH, valid(make_stored()))
    setup.script(setup.look_first_run, setup.click(A.STARTUP_USE_DEFAULT_FILE))

    assert setup.presenter.run()

    visible = _visible(setup.seen_first_run[0].buttons)
    assert A.STARTUP_USE_DEFAULT_FILE in visible
    assert A.STARTUP_CREATE_DEFAULT_FILE not in visible


def test_create_elsewhere_creates_the_chosen_file(setup: Setup) -> None:
    setup.stack.dialogs.chosen_path = "E:/data/mine.toml"
    setup.script(setup.click(A.STARTUP_CREATE_FILE_ELSEWHERE))

    assert setup.presenter.run()

    title, directory, name_filter = setup.stack.dialogs.texts("choose_save_file")[0]
    assert title == "en:startup.file_dialog.create_title"
    assert directory == DEFAULT_PATH.as_posix()
    assert name_filter == "en:startup.file_dialog.filter"
    assert setup.stack.preferences.get_text(DATA_FILE_PATH_KEY) == "E:/data/mine.toml"


def test_cancelled_picker_keeps_the_dialog_and_closing_it_quits(setup: Setup) -> None:
    setup.script(setup.click(A.STARTUP_CREATE_FILE_ELSEWHERE), setup.click(A.STARTUP_OPEN_EXISTING_FILE))

    assert not setup.presenter.run()

    assert setup.ui.shown == ["first_run"]
    assert setup.ui.closed == 0
    assert setup.stack.dialogs.kinds() == ["choose_save_file", "choose_open_file"]


def test_create_failure_is_shown_and_the_dialog_stays(setup: Setup) -> None:
    setup.stack.file.create_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS)
    setup.script(setup.click(A.STARTUP_CREATE_DEFAULT_FILE), setup.click(A.STARTUP_QUIT))

    assert not setup.presenter.run()

    assert setup.stack.dialogs.texts("error") == [
        ("en:startup.error.title", "en:error.storage_file_already_exists", "en:dialog.button.ok")
    ]
    assert setup.ui.closed == 1


def test_open_existing_damaged_file_moves_to_recovery_then_restores(setup: Setup) -> None:
    setup.stack.dialogs.chosen_path = DATA_PATH.as_posix()
    setup.stack.file.reports[DATA_PATH] = report(
        DATA_PATH,
        invalid(ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE),
        valid(make_stored(saved_at=SAVED_AT)),
        valid(make_stored(LanguageEnum.ENGLISH, saved_at=OLDER)),
    )
    setup.script(
        setup.click(A.STARTUP_OPEN_EXISTING_FILE),
        setup.look_recovery,
        lambda: setup.presenter.on_candidate_selected(1),
        setup.look_recovery,
        setup.click(A.STARTUP_RESTORE),
    )

    assert setup.presenter.run()

    assert setup.ui.shown == ["first_run", "recovery"]
    first, selected = setup.seen_recovery
    assert first.title == "en:startup.recovery.title"
    assert first.intro == "en:startup.recovery.intro.file_damaged"
    assert first.path == f"en:startup.recovery.path(path={DATA_PATH.as_posix()})"
    assert first.problems == ("en:error.storage_field_invalid_type",)
    assert first.candidates_caption == "en:startup.recovery.candidates"
    assert [candidate.selected for candidate in first.candidates] == [True, False]
    assert first.candidates[0].text.startswith("en:startup.recovery.candidate.temporary(saved_at=en:format.datetime(")
    assert [candidate.selected for candidate in selected.candidates] == [False, True]
    assert _visible(first.buttons) == [
        A.STARTUP_RESTORE,
        A.STARTUP_CHOOSE_ANOTHER_FILE,
        A.STARTUP_START_EMPTY,
        A.STARTUP_QUIT,
    ]
    assert ("restore:BACKUP", DATA_PATH) in setup.stack.file.calls


def test_selecting_the_same_candidate_does_not_re_render(setup: Setup) -> None:
    setup.presenter.on_candidate_selected(0)

    assert setup.stack.scheduler.pending_count == 0


def test_newer_tmp_offers_keep_current(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(
        DATA_PATH, valid(make_stored(saved_at=OLDER)), valid(make_stored(saved_at=SAVED_AT))
    )

    def file_fixed() -> None:
        setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored(saved_at=OLDER)))

    setup.script(setup.look_recovery, file_fixed, setup.click(A.STARTUP_KEEP_CURRENT_FILE))

    assert setup.presenter.run()

    snapshot = setup.seen_recovery[0]
    assert snapshot.intro == "en:startup.recovery.intro.newer_temporary"
    assert _visible(snapshot.buttons) == [A.STARTUP_RESTORE, A.STARTUP_KEEP_CURRENT_FILE, A.STARTUP_QUIT]
    assert [name for name, _path in setup.stack.file.calls][-2:] == ["discard", "probe"]


def test_locked_file_offers_retry_and_retry_reopens_it(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid(ErrorCodeEnum.STORAGE_FILE_UNREADABLE))

    def unlocked() -> None:
        setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored()))

    setup.script(setup.look_recovery, setup.click(A.STARTUP_RETRY), unlocked, setup.click(A.STARTUP_RETRY))

    assert setup.presenter.run()

    snapshot = setup.seen_recovery[0]
    assert snapshot.intro == "en:startup.recovery.intro.file_unreadable"
    assert _visible(snapshot.buttons) == [A.STARTUP_CHOOSE_ANOTHER_FILE, A.STARTUP_RETRY, A.STARTUP_QUIT]
    assert setup.ui.shown == ["recovery"]
    assert setup.recoveries


def test_missing_file_with_a_backup_offers_retry_and_retry_reopens_it(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, absent(), backup=valid(make_stored(saved_at=OLDER)))

    def put_back() -> None:
        setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored()))

    setup.script(setup.look_recovery, setup.click(A.STARTUP_RETRY), put_back, setup.click(A.STARTUP_RETRY))

    assert setup.presenter.run()

    snapshot = setup.seen_recovery[0]
    assert snapshot.intro == "en:startup.recovery.intro.file_missing"
    assert _visible(snapshot.buttons) == [
        A.STARTUP_RESTORE,
        A.STARTUP_CHOOSE_ANOTHER_FILE,
        A.STARTUP_START_EMPTY,
        A.STARTUP_RETRY,
        A.STARTUP_QUIT,
    ]
    assert setup.ui.shown == ["recovery"]
    assert [name for name, _path in setup.stack.file.calls if name.startswith(("restore", "create"))] == []


def test_missing_remembered_file_shows_the_notice_and_retry(setup: Setup) -> None:
    setup.remember()

    def connected() -> None:
        setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored()))

    setup.script(setup.look_first_run, setup.click(A.STARTUP_RETRY), connected, setup.click(A.STARTUP_RETRY))

    assert setup.presenter.run()

    snapshot = setup.seen_first_run[0]
    assert snapshot.notice == f"en:startup.first_run.not_found(path={DATA_PATH.as_posix()})"
    assert A.STARTUP_RETRY in _visible(snapshot.buttons)
    assert setup.ui.shown == ["first_run"]


def test_retry_at_first_run_resolves_again(setup: Setup) -> None:
    def remembered_elsewhere() -> None:
        setup.remember()
        setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, valid(make_stored()))

    setup.script(remembered_elsewhere, setup.click(A.STARTUP_RETRY))

    assert setup.presenter.run()


def test_start_empty_replaces_a_damaged_file(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.existing.add(DATA_PATH)
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid())
    setup.script(setup.click(A.STARTUP_START_EMPTY))

    assert setup.presenter.run()

    assert [name for name, _path in setup.stack.file.calls][-2:] == ["quarantine", "create"]


def test_choose_another_file_in_recovery(setup: Setup) -> None:
    other = DATA_PATH.with_name("other.toml")
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid(ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED))
    setup.stack.file.reports[other] = report(other, valid(make_stored()))
    setup.stack.dialogs.chosen_path = other.as_posix()
    setup.script(setup.look_recovery, setup.click(A.STARTUP_CHOOSE_ANOTHER_FILE))

    assert setup.presenter.run()

    assert setup.seen_recovery[0].intro == "en:startup.recovery.intro.newer_version"
    assert setup.stack.dialogs.texts("choose_open_file")[0][1] == DATA_PATH.parent.as_posix()
    assert setup.stack.preferences.get_text(DATA_FILE_PATH_KEY) == other.as_posix()


def test_restore_failure_is_shown(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid(), backup=valid(make_stored()))
    setup.stack.file.restore_failure = ValidationResult.failure(ErrorCodeEnum.STORAGE_DISK_FULL)
    setup.script(setup.click(A.STARTUP_RESTORE), setup.click(A.STARTUP_QUIT))

    assert not setup.presenter.run()

    assert setup.stack.dialogs.texts("error")[0][1] == "en:error.storage_disk_full"


def test_quit_from_recovery(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid())
    setup.script(setup.click(A.STARTUP_QUIT))

    assert not setup.presenter.run()


def test_buttons_are_disabled_while_their_action_is_busy(setup: Setup) -> None:
    def busy_check() -> None:
        setup.stack.gate.begin(A.STARTUP_QUIT)
        setup.look_first_run()

    setup.script(busy_check)

    assert not setup.presenter.run()

    quit_button = next(button for button in setup.seen_first_run[0].buttons if button.action is A.STARTUP_QUIT)
    assert not quit_button.enabled


def test_unrelated_action_does_nothing(setup: Setup) -> None:
    setup.script(setup.click(A.SHELL_SHOW_JOURNAL), setup.click(A.STARTUP_RESTORE), setup.click(A.STARTUP_QUIT))

    assert not setup.presenter.run()
    assert setup.stack.file.calls == []


def test_restore_without_a_candidate_is_skipped(setup: Setup) -> None:
    setup.remember()
    setup.stack.file.reports[DATA_PATH] = report(DATA_PATH, invalid())
    setup.script(setup.click(A.STARTUP_QUIT))
    setup.presenter.run()

    setup.presenter.on_action_requested(int(A.STARTUP_RESTORE))

    assert setup.presenter.plan is not None
    assert setup.presenter.plan.reason is StartupReasonEnum.FILE_DAMAGED


def test_action_before_run_is_ignored(setup: Setup) -> None:
    setup.presenter.on_action_requested(int(A.STARTUP_QUIT))

    assert setup.presenter.plan is None
    assert setup.presenter.build_first_run_snapshot() is None


def test_without_attached_dialogs_the_flow_quits(caplog: pytest.LogCaptureFixture) -> None:
    stack = StorageStack()
    presenter = StartupFlowPresenter(
        commands=stack.commands,
        dialogs=stack.dialogs,
        gate=stack.gate,
        renderer=stack.renderer,
        translator=stack.translator,
        formatter=stack.formatter,
    )

    assert not presenter.run()
    assert "not attached" in caplog.text
