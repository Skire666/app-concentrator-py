from pathlib import Path

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_keys import LAYOUT_JOURNAL_LEVELS, LAYOUT_MAIN_WINDOW_GEOMETRY
from concentrator.presentation.settings.settings_folder_enum import SettingsFolderEnum
from tests.fakes.fake_user_data_file import invalid, report, valid
from tests.fakes.settings_stack import ABOUT, SettingsStack
from tests.fakes.storage_stack import DATA_PATH
from tests.fakes.user_data_factory import make_stored

SWITCH = int(ActionIdEnum.SETTINGS_SWITCH_DATA_FILE)
MOVE = int(ActionIdEnum.SETTINGS_MOVE_DATA_FILE)
RESET = int(ActionIdEnum.SETTINGS_RESET_LAYOUT)
OTHER = Path("E:/other/concentrator.toml")
OPEN, CREATE, CANCEL = 0, 1, 2


@pytest.fixture
def stack() -> SettingsStack:
    return SettingsStack()


def test_file_sections_show_the_paths_and_the_version(stack: SettingsStack) -> None:
    files = stack.render().files

    assert files.data_file.current.path == DATA_PATH.as_posix()
    assert files.data_file.current.folder == int(SettingsFolderEnum.DATA_FILE)
    assert files.data_file.switch.text == "en:action.settings_switch_data_file"
    assert files.interface.reset_layout.enabled
    assert files.about.version == "0.4.0"
    assert [row.path for row in files.about.paths] == [
        ABOUT.app_config_file.as_posix(),
        ABOUT.ui_state_file.as_posix(),
        ABOUT.log_dir.as_posix(),
        ABOUT.backup_dir.as_posix(),
    ]


@pytest.mark.parametrize(
    ("folder", "expected"),
    [
        (SettingsFolderEnum.DATA_FILE, (DATA_PATH.parent, False)),
        (SettingsFolderEnum.APP_CONFIG, (ABOUT.app_config_file.parent, False)),
        (SettingsFolderEnum.UI_STATE, (ABOUT.ui_state_file.parent, True)),
        (SettingsFolderEnum.LOG, (ABOUT.log_dir, True)),
        (SettingsFolderEnum.BACKUP, (ABOUT.backup_dir, True)),
    ],
)
def test_open_folder_creates_only_missing_application_folders(
    stack: SettingsStack, folder: SettingsFolderEnum, expected: tuple[Path, bool]
) -> None:
    stack.files.on_open_folder(int(folder))

    assert stack.opener.opened == [expected]


def test_unknown_folder_is_not_opened(stack: SettingsStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.files.on_open_folder(99)

    assert stack.opener.opened == []
    assert "cannot be opened" in caplog.text


def test_reset_layout_removes_only_the_layout_keys_and_applies_the_defaults(stack: SettingsStack) -> None:
    preferences = stack.storage.preferences.values
    preferences.update({LAYOUT_MAIN_WINDOW_GEOMETRY: "AA==", LAYOUT_JOURNAL_LEVELS: "4,5"})
    preferences["storage/data_file_path"] = DATA_PATH.as_posix()

    stack.click(RESET, files=True)

    assert set(preferences) == {"storage/data_file_path"}
    assert stack.layout_resets == 1
    assert stack.dialogs.texts("confirm")[0][2] == "en:dialog.button.reset"


def test_reset_layout_cancelled_keeps_everything(stack: SettingsStack) -> None:
    stack.storage.preferences.values[LAYOUT_MAIN_WINDOW_GEOMETRY] = "AA=="
    stack.dialogs.confirm_answer = False

    stack.click(RESET, files=True)

    assert LAYOUT_MAIN_WINDOW_GEOMETRY in stack.storage.preferences.values
    assert stack.layout_resets == 0


def test_switch_to_a_valid_file_opens_it_and_says_so(stack: SettingsStack) -> None:
    stack.storage.file.reports[OTHER] = report(OTHER, valid(make_stored(LanguageEnum.FRENCH)))
    stack.dialogs.choices = [OPEN]
    stack.dialogs.chosen_path = OTHER.as_posix()

    stack.click(SWITCH, files=True)

    assert stack.data_commands.current_path == OTHER
    assert stack.dialogs.texts("choose_open_file")[0][1] == DATA_PATH.parent.as_posix()
    assert stack.dialogs.texts("inform")[0][1] == f"en:settings.switch.done(path={OTHER.as_posix()})"
    assert stack.last.files.data_file.current.path == OTHER.as_posix()


def test_switch_to_a_damaged_file_runs_the_recovery_dialog(stack: SettingsStack) -> None:
    stack.storage.file.reports[OTHER] = report(OTHER, invalid())
    stack.dialogs.choices = [OPEN]
    stack.dialogs.chosen_path = OTHER.as_posix()
    stack.recovery_opens = False

    stack.click(SWITCH, files=True)

    assert [plan.path for plan in stack.recovered] == [OTHER]
    assert stack.data_commands.current_path == DATA_PATH
    assert stack.dialogs.texts("inform") == []


def test_switch_after_a_successful_recovery_says_so(stack: SettingsStack) -> None:
    stack.storage.file.reports[OTHER] = report(OTHER, invalid())
    stack.dialogs.choices = [OPEN]
    stack.dialogs.chosen_path = OTHER.as_posix()

    stack.click(SWITCH, files=True)

    assert len(stack.dialogs.texts("inform")) == 1


def test_switch_to_the_current_file_is_explained(stack: SettingsStack) -> None:
    stack.dialogs.choices = [OPEN]
    stack.dialogs.chosen_path = DATA_PATH.as_posix()

    stack.click(SWITCH, files=True)

    assert stack.dialogs.texts("error")[0][1] == "en:error.storage_target_is_current_file"


def test_switch_to_a_missing_file_is_explained(stack: SettingsStack) -> None:
    stack.dialogs.choices = [OPEN]
    stack.dialogs.chosen_path = OTHER.as_posix()

    stack.click(SWITCH, files=True)

    assert stack.dialogs.texts("error")[0][1] == "en:error.storage_file_not_found"
    assert stack.recovered == []


def test_create_another_file_opens_it(stack: SettingsStack) -> None:
    stack.dialogs.choices = [CREATE]
    stack.dialogs.chosen_path = OTHER.as_posix()

    stack.click(SWITCH, files=True)

    assert stack.data_commands.current_path == OTHER
    assert stack.dialogs.kinds()[:2] == ["choose", "choose_save_file"]


@pytest.mark.parametrize(("choices", "path"), [([CANCEL], None), ([OPEN], None), ([CREATE], None)])
def test_switch_cancelled_changes_nothing(stack: SettingsStack, choices: list[int], path: str | None) -> None:
    stack.dialogs.choices = choices
    stack.dialogs.chosen_path = path

    stack.click(SWITCH, files=True)

    assert stack.data_commands.current_path == DATA_PATH
    assert "error" not in stack.dialogs.kinds()


def test_switch_with_unsaved_settings_asks_first(stack: SettingsStack) -> None:
    stack.presenter.on_log_level_selected(0)
    stack.dialogs.choices = [CANCEL]

    stack.click(SWITCH, files=True)

    assert stack.dialogs.texts("choose")[0][0] == "en:settings.leave.title"
    assert stack.presenter.has_unsaved_edits()
    assert len(stack.dialogs.texts("choose")) == 1


def test_switch_with_unsaved_settings_discarded_goes_on(stack: SettingsStack) -> None:
    stack.presenter.on_log_level_selected(0)
    stack.dialogs.choices = [1, CANCEL]

    stack.click(SWITCH, files=True)

    assert not stack.presenter.has_unsaved_edits()
    assert stack.dialogs.texts("choose")[1][0] == "en:settings.switch.title"


def test_move_writes_a_new_file_and_names_both(stack: SettingsStack) -> None:
    stack.dialogs.chosen_path = OTHER.as_posix()

    stack.click(MOVE, files=True)

    assert stack.data_commands.current_path == OTHER
    assert stack.dialogs.texts("choose_save_file")[0][1] == DATA_PATH.as_posix()
    assert stack.dialogs.texts("confirm")[0][2] == "en:dialog.button.move"
    assert stack.dialogs.texts("inform")[0][1] == (
        f"en:settings.move.done(current={OTHER.as_posix()},previous={DATA_PATH.as_posix()})"
    )


def test_move_not_confirmed_changes_nothing(stack: SettingsStack) -> None:
    stack.dialogs.chosen_path = OTHER.as_posix()
    stack.dialogs.confirm_answer = False

    stack.click(MOVE, files=True)

    assert stack.data_commands.current_path == DATA_PATH
    assert ("create", OTHER) not in stack.storage.file.calls


def test_move_picker_cancelled_changes_nothing(stack: SettingsStack) -> None:
    stack.click(MOVE, files=True)

    assert stack.dialogs.kinds() == ["choose_save_file"]


def test_move_failure_is_explained(stack: SettingsStack) -> None:
    stack.dialogs.chosen_path = DATA_PATH.as_posix()

    stack.click(MOVE, files=True)

    assert stack.dialogs.texts("error")[0][1] == "en:error.storage_target_is_current_file"


def test_without_open_file_the_file_commands_explain_it() -> None:
    stack = SettingsStack(attached=False)
    files = stack.render().files
    assert not files.data_file.move.enabled
    assert not files.data_file.current.open_folder.enabled
    assert not files.data_file.current.path

    stack.click(MOVE, files=True)
    stack.files.on_open_folder(int(SettingsFolderEnum.DATA_FILE))
    stack.dialogs.choices = [OPEN]
    stack.click(SWITCH, files=True)

    assert stack.dialogs.texts("error")[0][1] == "en:error.storage_file_not_found"
    assert stack.opener.opened == []
    assert not stack.dialogs.texts("choose_open_file")[0][1]


def test_unknown_file_action_is_logged(stack: SettingsStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.files.on_action_requested(int(ActionIdEnum.SETTINGS_SAVE))

    assert "not handled" in caplog.text
