"""Wiring of the user data storage: writer thread, TOML file, store, save coordinator, use cases."""

from dataclasses import dataclass

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.settings.language_hint import LanguageHint
from concentrator.application.settings.log_level_applier import LogLevelApplier
from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.data_file_commands import DataFileCommands
from concentrator.application.storage.external_change_commands import ExternalChangeCommands
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.startup_commands import StartupCommands
from concentrator.application.storage.storage_events import UserDataReplacedEvent
from concentrator.application.storage.user_data import UserDataLimits
from concentrator.application.storage.user_data_defaults import SectionDefaults, UserDataDefaults
from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.application.timer.timer_defaults import TimerDefaults
from concentrator.bootstrap.core import Core
from concentrator.infrastructure.logging.logging_control import LoggingControl
from concentrator.infrastructure.persistence.store_user_settings import StoreUserSettingsReader, StoreUserSettingsWriter
from concentrator.infrastructure.persistence.toml_user_data_file import TomlUserDataFile
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from concentrator.presentation.shell.language_switcher import LanguageSwitcher


@dataclass(frozen=True, slots=True, kw_only=True)
class Storage:
    """Everything that reads, keeps and saves the user data.

    Attributes:
        writer: The single writer thread (stopped on exit).
        store: In-memory data of the open file.
        timer_defaults: Timer values of ``concentrator.ini``.
        chime_defaults: Hourly chime values of ``concentrator.ini``.
        coordinator: Debounced saves and the shutdown flush.
        startup: First-run and recovery use cases.
        external: Answers to an external modification.
        data_files: "Use another file" and "Move file" of the settings page.
        settings_queries: Settings of the open file.
        switcher: Applies a UI language everywhere.
        hint: Language of the startup dialogs.
        app_version: Version written in the data file and shown in About.
    """

    writer: WriterThread
    store: UserDataStore
    timer_defaults: TimerDefaults
    chime_defaults: ChimeDefaults
    coordinator: SaveCoordinator
    startup: StartupCommands
    external: ExternalChangeCommands
    data_files: DataFileCommands
    settings_queries: SettingsQueries
    switcher: LanguageSwitcher
    hint: LanguageHint
    app_version: str


def _data_file(
    core: Core, config: AppConfig, writer: WriterThread, app_version: str, timer: TimerDefaults
) -> TomlUserDataFile:
    """Create the TOML data file adapter.

    Args:
        core: Main-thread services.
        config: Loaded configuration (``[settings]`` defaults of older files).
        writer: The single writer thread.
        app_version: Written in ``app_version``.
        timer: Bounds applied by the domain rules when a file is read.

    Returns:
        The adapter.
    """
    limits = UserDataLimits(timer=timer.limits, settings=SettingsDefaults.from_section(config.settings))
    return TomlUserDataFile(
        codec=UserDataCodec(app_version, limits),
        writer=writer,
        clock=core.clock,
        storage=config.storage,
        backup_dir=config.paths.backup_dir,
    )


def _startup_commands(
    core: Core,
    config: AppConfig,
    file: TomlUserDataFile,
    store: UserDataStore,
    coordinator: SaveCoordinator,
    defaults: UserDataDefaults,
) -> StartupCommands:
    """Create the first-run and recovery use cases.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        file: Data file adapter.
        store: In-memory data.
        coordinator: Save coordinator.
        defaults: Sections of new and older files.

    Returns:
        The use cases.
    """
    return StartupCommands(
        file=file,
        session=store,
        coordinator=coordinator,
        preferences=core.preferences,
        defaults=defaults,
        default_path=config.paths.default_data_file,
        event_bus=core.event_bus,
    )


def _user_data_defaults(core: Core, config: AppConfig, timer: TimerDefaults, chime: ChimeDefaults) -> UserDataDefaults:
    """Create the builder of new and completed data files.

    Args:
        core: Main-thread services (ids and clock).
        config: Loaded configuration (``[settings]`` values).
        timer: ``[timer]`` values.
        chime: ``[chime]`` values.

    Returns:
        The builder.
    """
    settings = SettingsDefaults.from_section(config.settings)
    return UserDataDefaults(core.ids, core.clock, SectionDefaults.from_defaults(timer, chime, settings))


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
    timer_defaults = TimerDefaults.from_section(config.timer)
    chime_defaults = ChimeDefaults.from_section(config.chime)
    file = _data_file(core, config, writer, app_version, timer_defaults)
    store = UserDataStore(core.event_bus)
    coordinator = SaveCoordinator(
        session=store, file=file, scheduler=core.scheduler, event_bus=core.event_bus, storage=config.storage
    )
    queries, hint, switcher = _settings_side(core, store, translator)
    startup, external, data_files = _file_use_cases(
        core, config, (file, store, coordinator), _user_data_defaults(core, config, timer_defaults, chime_defaults)
    )
    return Storage(
        writer=writer,
        store=store,
        timer_defaults=timer_defaults,
        chime_defaults=chime_defaults,
        coordinator=coordinator,
        startup=startup,
        external=external,
        data_files=data_files,
        settings_queries=queries,
        switcher=switcher,
        hint=hint,
        app_version=app_version,
    )


def _file_use_cases(
    core: Core,
    config: AppConfig,
    parts: tuple[TomlUserDataFile, UserDataStore, SaveCoordinator],
    defaults: UserDataDefaults,
) -> tuple[StartupCommands, ExternalChangeCommands, DataFileCommands]:
    """Create the use cases that open, reload, switch and move the data file.

    Args:
        core: Main-thread services.
        config: Loaded configuration.
        parts: Data file adapter, in-memory data and save coordinator.
        defaults: Sections of new and older files.

    Returns:
        The startup, external change and data file use cases.
    """
    file, store, coordinator = parts
    startup = _startup_commands(core, config, file, store, coordinator, defaults)
    external = ExternalChangeCommands(file, store, coordinator, defaults, core.event_bus)
    data_files = DataFileCommands(
        file=file, session=store, coordinator=coordinator, startup=startup, preferences=core.preferences
    )
    return startup, external, data_files


def _settings_side(
    core: Core, store: UserDataStore, translator: TranslatorPort
) -> tuple[SettingsQueries, LanguageHint, LanguageSwitcher]:
    """Create the settings queries (the log level follows them), the language hint and the switcher.

    Args:
        core: Main-thread services.
        store: In-memory data.
        translator: Translator switched by the language switcher.

    Returns:
        The queries, the hint and the switcher.
    """
    queries = SettingsQueries(StoreUserSettingsReader(store))
    _follow_log_level(core, queries)
    hint = LanguageHint(core.preferences)
    return queries, hint, _language_switcher(core, store, translator, hint)


def _follow_log_level(core: Core, queries: SettingsQueries) -> None:
    """Apply the log level of the user settings once a data file is open, and when it changes.

    Args:
        core: Main-thread services (event bus).
        queries: Settings of the open data file.
    """
    applier = LogLevelApplier(queries, LoggingControl())
    core.event_bus.subscribe(UserDataReplacedEvent, applier.on_user_data_replaced)
    core.event_bus.subscribe(UserSettingsChangedEvent, applier.on_settings_changed)


def _language_switcher(
    core: Core, store: UserDataStore, translator: TranslatorPort, hint: LanguageHint
) -> LanguageSwitcher:
    """Create the language switcher on top of the settings use cases.

    Args:
        core: Main-thread services.
        store: In-memory data.
        translator: Translator to switch.
        hint: Language of the startup dialogs.

    Returns:
        The switcher.
    """
    settings = SettingsCommands(
        StoreUserSettingsReader(store), StoreUserSettingsWriter(store), core.clock, core.event_bus
    )
    return LanguageSwitcher(translator, hint, core.renderer, settings)
