"""Startup and shutdown sequence (phase 0 spec "Bootstrap", phase 1 storage steps, ADR-027, ADR-032)."""

import logging
import os
import sys
from dataclasses import dataclass
from importlib import metadata
from typing import Final

from PySide6.QtGui import QIcon, QSessionManager
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.bootstrap.core import build_core
from concentrator.bootstrap.runtime import Runtime, configure_runtime
from concentrator.bootstrap.self_check import run_self_check
from concentrator.bootstrap.shell import Shell, ShellServices, build_shell
from concentrator.bootstrap.startup import open_data_file
from concentrator.bootstrap.startup_errors import show_config_error
from concentrator.bootstrap.storage import build_storage
from concentrator.bootstrap.translator_loader import load_translator
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.config.ini_config_loader import IniConfigLoader
from concentrator.infrastructure.qt.qt_single_instance_guard import QtSingleInstanceGuard
from concentrator.infrastructure.system import windows_shell
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.storage.startup_dialog_layout import StartupDialogLayout
from concentrator.ui.support.window_activation import bring_modal_dialog_to_front

_logger = logging.getLogger(__name__)

SELF_CHECK_VARIABLE: Final = "CONCENTRATOR_SELF_CHECK"
SELF_CHECK_ON: Final = "1"
EXIT_OK: Final = 0
EXIT_FAILURE: Final = 1
PACKAGE_NAME: Final = "concentrator"
UNKNOWN_VERSION: Final = "unknown"


def _version() -> str:
    """Return the installed version (bundled metadata when frozen).

    Returns:
        The version, or ``unknown``.
    """
    try:
        return metadata.version(PACKAGE_NAME)
    except metadata.PackageNotFoundError:
        return UNKNOWN_VERSION


def _application(config: AppConfig | None, paths: AppPaths) -> QApplication:
    """Create the ``QApplication`` (reused if one exists, as in tests) with names and icon (step 2).

    Args:
        config: Loaded configuration, ``None`` when it failed.
        paths: Application paths.

    Returns:
        The application.
    """
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    if config is not None:
        app.setOrganizationName(config.app.organization)
        app.setApplicationName(config.app.name)
    app.setWindowIcon(QIcon(str(paths.app_icon_file)))
    return app


@dataclass(frozen=True, slots=True)
class InstanceCheck:
    """Outcome of the single-instance step.

    Attributes:
        other_instance_running: Another instance runs and was asked to show itself: exit with 0.
        guard: Guard holding the lock, ``None`` when running unguarded after a lock error.
    """

    other_instance_running: bool
    guard: QtSingleInstanceGuard | None


def acquire_single_instance(app: QApplication, config: AppConfig, paths: AppPaths) -> InstanceCheck:
    """Step 4: take the per-user lock or ask the running instance to show itself.

    Args:
        app: Owner of the local server.
        config: Loaded configuration.
        paths: Application paths (lock folder ``{localappdata}/<app.name>``).

    Returns:
        The outcome; a lock error is logged and the application runs unguarded.
    """
    lock_dir = paths.resolve(f"{{localappdata}}/{config.app.name}", "app.name")
    if lock_dir.data is None:
        _logger.error("No folder for the instance lock; running without single-instance protection")
        return InstanceCheck(other_instance_running=False, guard=None)
    guard = QtSingleInstanceGuard(
        lock_dir=lock_dir.data,
        key=config.app.single_instance_key,
        timeout_ms=config.app.single_instance_timeout_ms,
        parent=app,
    )
    result = guard.acquire(before_notify=windows_shell.allow_set_foreground_window)
    _log_issues("Single instance", result.validation)
    if result.data is False:
        _logger.info("Another instance is running; it was asked to show itself")
        return InstanceCheck(other_instance_running=True, guard=None)
    if result.data is None:
        _logger.error("Single-instance check failed; running without protection")
        return InstanceCheck(other_instance_running=False, guard=None)
    _logger.info("Single-instance lock acquired")
    return InstanceCheck(other_instance_running=False, guard=guard)


def _log_issues(step: str, validation: ValidationResult) -> None:
    """Log the warnings and failures of a startup step.

    Args:
        step: Step name.
        validation: Its result.
    """
    if validation.issues:
        _logger.warning("%s: %s", step, [code.name for code in validation.error_codes])


def claim_instance(app: QApplication, config: AppConfig, paths: AppPaths, runtime: Runtime) -> InstanceCheck:
    """Step 4, then the log file for the process that keeps running (ADR-026).

    A launch that hands over to the running instance exits without opening the log file; otherwise
    (lock held, or unguarded after a lock error) the rotating file is attached and receives the
    buffered startup records.

    Args:
        app: The application.
        config: Loaded configuration.
        paths: Application paths.
        runtime: Installed services (logging still in stage 1).

    Returns:
        The single-instance outcome.
    """
    instance = acquire_single_instance(app, config, paths)
    if not instance.other_instance_running:
        runtime.logging.attach_log_file()
    return instance


def _run_shell(app: QApplication, shell: Shell, guard: QtSingleInstanceGuard | None) -> int:
    """Steps 7 to 9: show the window, run the event loop; flush on session end and on quit (ADR-032).

    Args:
        app: The application.
        shell: Wired window.
        guard: Instance guard, ``None`` when unguarded.

    Returns:
        The event loop exit code.
    """
    if guard is not None:
        guard.set_activation_handler(shell.window.bring_to_front)

    def on_commit_data(_manager: QSessionManager) -> None:
        _logger.info("Windows session ending")
        shell.shutdown_presenter.flush_on_session_end()

    def on_about_to_quit() -> None:
        shell.shutdown()
        _logger.info("Shutting down")

    app.commitDataRequest.connect(on_commit_data)
    app.aboutToQuit.connect(on_about_to_quit)
    shell.start()
    return app.exec()


def _run_window(app: QApplication, config: AppConfig, paths: AppPaths, runtime: Runtime) -> int:
    """Steps 4 to 9: instance and log file, catalogs, data file (ADR-027), window, event loop, shutdown.

    Args:
        app: The application.
        config: Loaded configuration.
        paths: Application paths.
        runtime: Installed services; its reporter receives the unexpected errors.

    Returns:
        The process exit code (0 also when the user quits the startup dialogs).
    """
    instance = claim_instance(app, config, paths, runtime)
    if instance.other_instance_running:
        return EXIT_OK
    translator = load_translator(paths, config)
    core = build_core(app, config, runtime.reporter)
    storage = build_storage(core, config, translator, runtime.reporter, _version())
    if instance.guard is not None:
        instance.guard.set_activation_handler(bring_modal_dialog_to_front)
    try:
        protection = InstanceProtectionPresenter(translator, protected=instance.guard is not None)
        services = ShellServices(core=core, storage=storage, instance=protection, feed=runtime.logging.ring_buffer)
        return _run_with_data_file(app, (config, paths, translator), runtime, services, instance.guard)
    finally:
        storage.writer.shutdown()
        if instance.guard is not None:
            instance.guard.release()


def _run_with_data_file(
    app: QApplication,
    setup: tuple[AppConfig, AppPaths, TranslatorPort],
    runtime: Runtime,
    services: ShellServices,
    guard: QtSingleInstanceGuard | None,
) -> int:
    """Steps 5 to 9: data file (ADR-027), window, event loop.

    Args:
        app: The application.
        setup: Loaded configuration, application paths and translator.
        runtime: Installed services; its reporter receives the unexpected errors.
        services: Core, storage, single-instance indicator and log buffer.
        guard: Instance guard, ``None`` when unguarded.

    Returns:
        The process exit code (0 also when the user quits the startup dialogs).
    """
    config, paths, translator = setup
    icon = QIcon(str(paths.app_icon_file))
    layout = StartupDialogLayout.from_ui_section(config.ui)
    if not open_data_file(services.core, services.storage, translator, services.instance, icon, layout):
        return EXIT_OK
    shell = build_shell(app, config, paths, translator, runtime.reporter, services)
    return _run_shell(app, shell, guard)


def run(paths: AppPaths, *, self_check: bool) -> int:
    """Run the startup sequence, the event loop and the shutdown.

    Args:
        paths: Application paths.
        self_check: Validate the installation and exit instead of showing the window.

    Returns:
        The process exit code.
    """
    config = IniConfigLoader(paths).load(paths.config_file)
    model_id = windows_shell.set_app_user_model_id(config.data.app.app_user_model_id) if config.data else None
    app = _application(config.data, paths)
    if config.data is None:
        if not self_check:
            show_config_error(config.validation, paths.config_file)
        return EXIT_FAILURE
    runtime = configure_runtime(config.data)
    try:
        _logger.info(
            "Concentrator %s starting (frozen: %s, ini: %s)",
            _version(),
            getattr(sys, "frozen", False),
            paths.config_file,
        )
        _log_issues("AppUserModelID", model_id or ValidationResult.success())
        if self_check:
            runtime.logging.attach_log_file()
            return EXIT_OK if run_self_check(paths, config.data, _version()) else EXIT_FAILURE
        exit_code = _run_window(app, config.data, paths, runtime)
        _logger.info("Exit code %d", exit_code)
        return exit_code
    finally:
        runtime.shutdown()


def main() -> int:
    """Entry point of ``python -m concentrator`` and of the ``concentrator`` gui-script.

    Returns:
        The process exit code.
    """
    return run(AppPaths.from_runtime(), self_check=os.environ.get(SELF_CHECK_VARIABLE) == SELF_CHECK_ON)
