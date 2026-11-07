import logging
import shutil
from pathlib import Path

import pytest
from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox
from pytestqt.qtbot import QtBot

from concentrator.application.common.app_config import AppConfig
from concentrator.bootstrap.app import acquire_single_instance, run
from concentrator.bootstrap.core import Core, build_core
from concentrator.bootstrap.runtime import ForwardingErrorReporter
from concentrator.bootstrap.self_check import storage_failures
from concentrator.bootstrap.shell import build_shell
from concentrator.bootstrap.startup import apply_language_hint, open_data_file
from concentrator.bootstrap.startup_errors import format_config_error
from concentrator.bootstrap.storage import Storage, build_storage
from concentrator.bootstrap.translator_loader import load_translator
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.storage.startup_dialog_layout import StartupDialogLayout
from tests.fakes.app_config_factory import make_app_config
from tests.fakes.recording_error_reporter import RecordingErrorReporter

pytestmark = pytest.mark.ui

REAL_PATHS = AppPaths.from_runtime()


def _app() -> QApplication:
    application = QApplication.instance()
    assert isinstance(application, QApplication)
    return application


class _Install:
    """A temporary installation: ini next to a fake exe folder, user folders under ``tmp_path``."""

    def __init__(
        self, root: Path, *, ini_replacements: dict[str, str] | None = None, copy_assets: bool = False
    ) -> None:
        self.root = root
        app_dir = root / "app"
        app_dir.mkdir()
        text = REAL_PATHS.config_file.read_text(encoding="utf-8")
        for old, new in (ini_replacements or {}).items():
            text = text.replace(old, new)
        (app_dir / "concentrator.ini").write_text(text, encoding="utf-8")
        assets_dir = REAL_PATHS.assets_dir
        if copy_assets:
            assets_dir = root / "assets"
            shutil.copytree(REAL_PATHS.assets_dir, assets_dir)
        environment = {"APPDATA": str(root / "roaming"), "LOCALAPPDATA": str(root / "local")}
        self.paths = AppPaths(app_dir, assets_dir, app_dir / "concentrator.ini", environment)

    @property
    def log_text(self) -> str:
        return (self.root / "local" / "Concentrator" / "logs" / "concentrator.log").read_text(encoding="utf-8")

    def config(self) -> AppConfig:
        config = IniConfigLoader(self.paths).load(self.paths.config_file).data
        assert config is not None
        return config


@pytest.fixture
def install(qtbot: QtBot, tmp_path: Path) -> _Install:
    del qtbot  # ensures the QApplication exists
    return _Install(tmp_path)


def test_self_check_passes_and_logs_the_startup(install: _Install) -> None:
    assert run(install.paths, self_check=True) == 0

    log = install.log_text
    assert "Concentrator" in log
    assert "starting" in log
    assert "Self-check passed" in log


def test_self_check_fails_when_a_catalog_is_missing(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    install = _Install(tmp_path, copy_assets=True)
    (install.paths.i18n_dir / "fr.json").unlink()

    assert run(install.paths, self_check=True) == 1
    assert "Self-check failed" in install.log_text


def test_self_check_fails_when_a_module_icon_is_missing(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    install = _Install(tmp_path, copy_assets=True)
    (install.paths.icons_dir / "module-journal.svg").unlink()

    assert run(install.paths, self_check=True) == 1
    assert "module-journal.svg" in install.log_text


def test_invalid_ini_exits_with_failure(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    install = _Install(tmp_path, ini_replacements={"module_bar_width_px = 100\n": ""})

    assert run(install.paths, self_check=True) == 1


def test_config_error_text_names_the_file_the_codes_and_the_keys() -> None:
    validation = ValidationResult.failure(ErrorCodeEnum.CONFIG_KEY_MISSING, field="ui.module_bar_width_px").merge(
        ValidationResult.failure(ErrorCodeEnum.CONFIG_FILE_NOT_FOUND)
    )

    text = format_config_error(validation, Path("E:/Apps/Concentrator/concentrator.ini"))

    assert str(Path("E:/Apps/Concentrator/concentrator.ini")) in text
    assert "- CONFIG_KEY_MISSING (3003): ui.module_bar_width_px" in text
    assert "- CONFIG_FILE_NOT_FOUND (3001)\n" in text


def _storage(config: AppConfig, install: _Install) -> tuple[Core, Storage, JsonCatalogTranslator]:
    translator = load_translator(install.paths, config)
    core = build_core(_app(), config, ForwardingErrorReporter())
    return core, build_storage(core, config, translator, ForwardingErrorReporter(), "0.1.0-test"), translator


def test_built_shell_starts_ticks_saves_and_flushes_on_shutdown(qtbot: QtBot, install: _Install) -> None:
    config = install.config()
    core, storage, translator = _storage(config, install)
    assert storage.startup.create_at(config.paths.default_data_file, LanguageEnum.ENGLISH).is_success
    protection = InstanceProtectionPresenter(translator, protected=True)
    shell = build_shell(
        _app(),
        config,
        install.paths,
        translator,
        ForwardingErrorReporter(),
        core=core,
        storage=storage,
        instance=protection,
    )
    qtbot.addWidget(shell.window)

    shell.start()
    qtbot.waitExposed(shell.window)
    shell.window.status_bar.language_button.click()
    qtbot.waitUntil(lambda: not core.gate.is_busy(ActionIdEnum.SHELL_TOGGLE_LANGUAGE), timeout=2000)

    assert shell.window.windowTitle() == "Concentrator"
    assert shell.window.module_bar.width() == config.ui.module_bar_width_px
    assert shell.tick_timer.isActive()
    assert shell.tick_timer.interval() == config.timer.tick_interval_ms
    shell.shutdown()
    core.renderer.flush()  # renders the final save state while the window still exists
    storage.writer.shutdown()
    assert not shell.tick_timer.isActive()
    assert "layout" in config.paths.ui_state_file.read_text(encoding="utf-8")
    assert "language = 2" in config.paths.default_data_file.read_text(encoding="utf-8")


def test_reopening_a_remembered_file_needs_no_dialog_and_follows_its_language(qtbot: QtBot, install: _Install) -> None:
    del qtbot
    config = install.config()
    _core, first, _translator = _storage(config, install)
    first.startup.create_at(config.paths.default_data_file, LanguageEnum.FRENCH)
    first.writer.shutdown()
    core, storage, translator = _storage(config, install)
    protection = InstanceProtectionPresenter(translator, protected=True)

    opened = open_data_file(
        core, storage, translator, protection, QIcon(), StartupDialogLayout.from_ui_section(config.ui)
    )

    storage.writer.shutdown()
    assert opened
    assert translator.language is LanguageEnum.FRENCH
    assert storage.hint.read() is LanguageEnum.FRENCH


def test_language_hint_is_applied_before_the_startup_dialogs(qtbot: QtBot, install: _Install) -> None:
    del qtbot
    config = install.config()
    core, storage, translator = _storage(config, install)
    storage.hint.write(LanguageEnum.FRENCH)
    core.preferences.set_text("shell/language_hint", "de")

    apply_language_hint(storage, translator)
    assert translator.language is LanguageEnum.ENGLISH
    storage.hint.write(LanguageEnum.FRENCH)
    apply_language_hint(storage, translator)
    storage.writer.shutdown()

    assert translator.language is LanguageEnum.FRENCH


def test_unguarded_startup_warns_before_opening_the_file(
    qtbot: QtBot, install: _Install, caplog: pytest.LogCaptureFixture
) -> None:
    del qtbot
    config = install.config()
    _core, first, _translator = _storage(config, install)
    first.startup.create_at(config.paths.default_data_file, LanguageEnum.ENGLISH)
    first.writer.shutdown()
    core, storage, translator = _storage(config, install)
    protection = InstanceProtectionPresenter(translator, protected=False)
    titles: list[str] = []

    def accept_warning() -> None:
        box = QApplication.activeModalWidget()
        assert isinstance(box, QMessageBox)
        titles.append(box.windowTitle())
        box.buttons()[0].click()

    QTimer.singleShot(0, accept_warning)
    with caplog.at_level(logging.INFO):
        opened = open_data_file(
            core, storage, translator, protection, QIcon(), StartupDialogLayout.from_ui_section(config.ui)
        )
    storage.writer.shutdown()

    assert opened
    assert titles == ["Single-instance check unavailable"]
    assert "Unguarded single-instance warning shown" in caplog.text


def test_self_check_round_trips_the_user_data() -> None:
    assert storage_failures("0.1.0", make_app_config()) == []


def test_second_instance_check_in_the_same_session_asks_to_exit(install: _Install) -> None:
    config = install.config()
    first = acquire_single_instance(_app(), config, install.paths)
    assert first.guard is not None

    second = acquire_single_instance(_app(), config, install.paths)

    first.guard.release()
    assert second.other_instance_running
    assert second.guard is None


def test_unresolvable_lock_folder_runs_unguarded(install: _Install, caplog: pytest.LogCaptureFixture) -> None:
    paths = AppPaths(install.paths.app_dir, install.paths.assets_dir, install.paths.config_file, {})

    with caplog.at_level(logging.ERROR, logger="concentrator.bootstrap.app"):
        check = acquire_single_instance(_app(), install.config(), paths)

    assert not check.other_instance_running
    assert check.guard is None
    assert caplog.records


def test_translator_falls_back_to_keys_when_catalogs_fail(qtbot: QtBot, tmp_path: Path) -> None:
    del qtbot
    install = _Install(tmp_path, copy_assets=True)
    shutil.rmtree(install.paths.i18n_dir)

    translator = load_translator(install.paths, install.config())

    assert translator.tr("app.title") == "app.title"


def test_forwarding_reporter_forwards_once_connected() -> None:
    reporter = ForwardingErrorReporter()
    target = RecordingErrorReporter()
    reporter.report(ValueError("before"))

    reporter.connect(target)
    reporter.report(KeyError("after"))

    assert [type(error) for error in target.errors] == [KeyError]
