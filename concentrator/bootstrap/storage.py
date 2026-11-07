"""Wiring of the user data storage: writer thread, TOML file, store, save coordinator, use cases."""

from dataclasses import dataclass

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.language_hint import LanguageHint
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.external_change_commands import ExternalChangeCommands
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.bootstrap.core import Core
from concentrator.infrastructure.persistence.store_user_settings import StoreUserSettingsReader, StoreUserSettingsWriter
from concentrator.infrastructure.persistence.toml_user_data_file import TomlUserDataFile
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from concentrator.infrastructure.system.uuid7_id_generator import Uuid7IdGenerator
from concentrator.presentation.shell.language_switcher import LanguageSwitcher


@dataclass(frozen=True, slots=True, kw_only=True)
class Storage:
    """Everything that reads, keeps and saves the user data.

    Attributes:
        writer: The single writer thread (stopped on exit).
        coordinator: Debounced saves and the shutdown flush.
        startup: First-run and recovery use cases.
        external: Answers to an external modification.
        settings_queries: Settings of the open file.
        switcher: Applies a UI language everywhere.
        hint: Language of the startup dialogs.
    """

    writer: WriterThread
    coordinator: SaveCoordinator
    startup: StartupCommands
    external: ExternalChangeCommands
    settings_queries: SettingsQueries
    switcher: LanguageSwitcher
    hint: LanguageHint


def _data_file(core: Core, config: AppConfig, writer: WriterThread, app_version: str) -> TomlUserDataFile:
    """Create the TOML data file adapter.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        writer: The single writer thread.
        app_version: Written in ``app_version``.

    Returns:
        The adapter.
    """
    return TomlUserDataFile(
        codec=UserDataCodec(app_version),
        writer=writer,
        clock=core.clock,
        storage=config.storage,
        backup_dir=config.paths.backup_dir,
    )


def _startup_commands(
    core: Core, config: AppConfig, file: TomlUserDataFile, store: UserDataStore, coordinator: SaveCoordinator
) -> StartupCommands:
    """Create the first-run and recovery use cases.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        file: Data file adapter.
        store: In-memory data.
        coordinator: Save coordinator.

    Returns:
        The use cases.
    """
    return StartupCommands(
        file=file,
        session=store,
        coordinator=coordinator,
        preferences=core.preferences,
        ids=Uuid7IdGenerator(),
        clock=core.clock,
        default_path=config.paths.default_data_file,
    )


def build_storage(
    core: Core, config: AppConfig, translator: TranslatorPort, reporter: ErrorReporterPort, app_version: str
) -> Storage:
    """Create the storage side.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        translator: Translator switched by the language switcher.
        reporter: Receives the exceptions of writer jobs.
        app_version: Written in ``app_version``.

    Returns:
        The storage services.
    """
    writer = WriterThread(core.dispatcher, reporter)
    file = _data_file(core, config, writer, app_version)
    store = UserDataStore(core.event_bus)
    coordinator = SaveCoordinator(
        session=store, file=file, scheduler=core.scheduler, event_bus=core.event_bus, storage=config.storage
    )
    reader = StoreUserSettingsReader(store)
    settings = SettingsCommands(reader, StoreUserSettingsWriter(store), core.clock, core.event_bus)
    hint = LanguageHint(core.preferences)
    return Storage(
        writer=writer,
        coordinator=coordinator,
        startup=_startup_commands(core, config, file, store, coordinator),
        external=ExternalChangeCommands(file, store, coordinator),
        settings_queries=SettingsQueries(reader),
        switcher=LanguageSwitcher(translator, hint, core.renderer, settings),
        hint=hint,
    )
