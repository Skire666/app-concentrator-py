from collections.abc import Callable
from datetime import timedelta

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from pytestqt.qtbot import QtBot

from concentrator.application.storage.startup_commands import DATA_FILE_PATH_KEY
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.storage.startup_flow_presenter import StartupFlowPresenter
from concentrator.ui.widgets.button_column_widget import ButtonColumnWidget
from concentrator.ui.widgets.snapshot_button import SnapshotButton
from concentrator.ui.windows.startup_dialogs import StartupDialogs
from tests.fakes.fake_user_data_file import invalid, report, valid
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_stored

pytestmark = pytest.mark.ui


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
        self.dialogs = StartupDialogs(self.presenter, self.stack.renderer, QIcon())
        self.presenter.attach(self.dialogs)
        self.checks: list[Callable[[], None]] = []

    def later(self, step: Callable[[], None]) -> None:
        """Run a step inside the modal loop of the next dialog."""

        def run() -> None:
            self.stack.scheduler.run_pending()
            step()

        QTimer.singleShot(0, run)


def _button(column: ButtonColumnWidget, action: ActionIdEnum) -> SnapshotButton:
    texts = {button.text(): button for button in column.buttons}
    return texts[f"en:action.{action.name.lower()}"]


@pytest.fixture
def setup(qtbot: QtBot) -> Setup:
    built = Setup()
    qtbot.addWidget(built.dialogs.first_run)
    qtbot.addWidget(built.dialogs.recovery)
    return built


def test_first_run_dialog_renders_and_creates_the_file(setup: Setup) -> None:
    seen: dict[str, object] = {}

    def look_and_click() -> None:
        panel = setup.dialogs.first_run.panel
        seen["title"] = setup.dialogs.first_run.windowTitle()
        seen["visible"] = [button.text() for button in panel.buttons.buttons if not button.isHidden()]
        seen["notice"] = panel.notice_text
        _button(panel.buttons, ActionIdEnum.STARTUP_CREATE_DEFAULT_FILE).click()

    setup.later(look_and_click)

    assert setup.presenter.run()

    assert seen["title"] == "en:startup.first_run.title"
    assert not seen["notice"]
    assert seen["visible"] == [
        "en:action.startup_create_default_file",
        "en:action.startup_create_file_elsewhere",
        "en:action.startup_open_existing_file",
        "en:action.startup_quit",
    ]
    assert not setup.dialogs.first_run.isVisible()


def test_closing_the_dialog_quits(setup: Setup) -> None:
    setup.later(setup.dialogs.first_run.reject)

    assert not setup.presenter.run()


def test_recovery_dialog_lists_candidates_and_restores_the_selected_one(setup: Setup) -> None:
    setup.stack.preferences.values[DATA_FILE_PATH_KEY] = DATA_PATH.as_posix()
    setup.stack.file.reports[DATA_PATH] = report(
        DATA_PATH,
        invalid(ErrorCodeEnum.STORAGE_FIELD_MISSING),
        valid(make_stored(saved_at=SAVED_AT)),
        valid(make_stored(saved_at=SAVED_AT - timedelta(hours=1))),
    )
    seen: dict[str, object] = {}

    def select_and_restore() -> None:
        panel = setup.dialogs.recovery.panel
        seen["rows"] = panel.candidates.count()
        seen["problems"] = panel.problems_text
        panel.candidates.setCurrentRow(1)
        setup.stack.scheduler.run_pending()
        seen["current"] = panel.candidates.currentRow()
        _button(panel.buttons, ActionIdEnum.STARTUP_RESTORE).click()

    setup.later(select_and_restore)

    assert setup.presenter.run()

    assert seen == {"rows": 2, "problems": "en:error.storage_field_missing", "current": 1}
    assert ("restore:BACKUP", DATA_PATH) in setup.stack.file.calls


def test_button_column_hides_extra_buttons(qtbot: QtBot) -> None:
    column = ButtonColumnWidget()
    qtbot.addWidget(column)
    snapshot = ButtonSnapshot(text="A", tooltip="", enabled=True, visible=True, action=ActionIdEnum.STARTUP_QUIT)

    column.render_snapshot((snapshot, snapshot))
    column.render_snapshot((snapshot,))

    assert len(column.buttons) == 2
    assert column.buttons[1].isHidden()


def test_dialog_ignores_an_empty_snapshot(setup: Setup) -> None:
    setup.dialogs.first_run.render_snapshot(None)
    setup.dialogs.recovery.render_snapshot(None)

    assert not setup.dialogs.first_run.windowTitle()
    assert not setup.dialogs.recovery.windowTitle()
