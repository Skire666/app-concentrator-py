"""Wiring of the settings page (Menu C): form, file sections and their use cases."""

import logging

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.bootstrap.shell_services import ShellServices
from concentrator.bootstrap.timer import TimerServices
from concentrator.infrastructure.persistence.store_hourly_chime import StoreHourlyChimeReader, StoreHourlyChimeWriter
from concentrator.infrastructure.persistence.store_user_settings import StoreUserSettingsReader, StoreUserSettingsWriter
from concentrator.infrastructure.qt.qt_link_opener import QtLinkOpener
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.settings.about_info import AboutInfo
from concentrator.presentation.settings.data_file_flow import DataFileFlow, DataFileServices
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter, SettingsFilesServices
from concentrator.presentation.settings.settings_presenter import SettingsPresenter, SettingsServices

_logger = logging.getLogger(__name__)


def _no_recovery(plan: StartupPlan) -> bool:
    """Recovery used when the shell is built without the startup flow (tests): nothing opens.

    Args:
        plan: Plan of the chosen file.

    Returns:
        ``False``.
    """
    _logger.warning("No recovery dialog for %s: startup flow not available", plan.path)
    return False


def build_settings(
    config: AppConfig, paths: AppPaths, translator: TranslatorPort, services: ShellServices, timer: TimerServices
) -> tuple[SettingsPresenter, SettingsFilesPresenter]:
    """Create the settings presenters (the form presenter owns the file sections presenter).

    Args:
        config: Loaded configuration.
        paths: Application paths (``concentrator.ini``).
        translator: Current-language translator.
        services: Core, storage and startup flow.
        timer: Sounds and preview.

    Returns:
        The form presenter and the file sections presenter.
    """
    core, storage = services.core, services.storage
    store = storage.store
    form_services = SettingsServices(
        settings_queries=storage.settings_queries,
        settings_commands=SettingsCommands(
            StoreUserSettingsReader(store), StoreUserSettingsWriter(store), core.clock, core.event_bus
        ),
        defaults=SettingsDefaults.from_section(config.settings),
        chime_queries=ChimeQueries(StoreHourlyChimeReader(store), storage.chime_defaults),
        chime_commands=ChimeCommands(
            StoreHourlyChimeReader(store), StoreHourlyChimeWriter(store), core.clock, core.event_bus
        ),
        sounds=timer.queries,
        preview=timer.preview,
        switcher=storage.switcher,
    )
    files_services = _files_services(config, paths, translator, services)
    files = SettingsFilesPresenter(translator, core.gate, core.renderer, files_services)
    return SettingsPresenter(translator, core.gate, core.renderer, form_services, files), files


def _files_services(
    config: AppConfig, paths: AppPaths, translator: TranslatorPort, services: ShellServices
) -> SettingsFilesServices:
    """Create what the file sections drive.

    Args:
        config: Loaded configuration (paths).
        paths: Application paths (``concentrator.ini``).
        translator: Current-language translator.
        services: Core, storage and startup flow.

    Returns:
        The services.
    """
    storage = services.storage
    startup = services.startup
    flow = DataFileFlow(
        translator,
        DataFileServices(
            commands=storage.data_files,
            settings=storage.settings_queries,
            switcher=storage.switcher,
            recovery=_no_recovery if startup is None else startup.presenter.resume,
        ),
    )
    about = AboutInfo(
        version=storage.app_version,
        app_config_file=paths.config_file,
        ui_state_file=config.paths.ui_state_file,
        log_dir=config.paths.log_dir,
        backup_dir=config.paths.backup_dir,
    )
    return SettingsFilesServices(
        data_file=flow,
        current_path=lambda: storage.data_files.current_path,
        opener=QtLinkOpener(),
        layout=LayoutStateKeeper(services.core.preferences),
        about=about,
    )
