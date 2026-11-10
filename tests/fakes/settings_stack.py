"""The settings presenters wired with fakes, on top of the storage and timer stacks."""

from pathlib import Path
from typing import Final

from concentrator.application.settings.settings_commands import SettingsCommands
from concentrator.application.settings.settings_events import UserSettingsChangedEvent
from concentrator.application.settings.settings_queries import SettingsQueries
from concentrator.application.storage.data_file_commands import DataFileCommands
from concentrator.application.storage.startup_plan import StartupPlan
from concentrator.application.timer.timer_events import HourlyChimeChangedEvent
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.settings.about_info import AboutInfo
from concentrator.presentation.settings.data_file_flow import DataFileFlow, DataFileServices
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter, SettingsFilesServices
from concentrator.presentation.settings.settings_presenter import SettingsPresenter, SettingsServices
from concentrator.presentation.settings.settings_snapshot import SettingsSnapshot
from tests.fakes.fake_desktop import FakeLinkOpener
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.timer_stack import TimerStack
from tests.fakes.user_data_factory import SAVED_AT, SETTINGS_DEFAULTS

ABOUT: Final = AboutInfo(
    version="0.4.0",
    app_config_file=Path("C:/Program Files/Concentrator/concentrator.ini"),
    ui_state_file=Path("C:/Users/me/AppData/Roaming/Concentrator/ui-state.ini"),
    log_dir=Path("C:/Users/me/AppData/Local/Concentrator/logs"),
    backup_dir=Path("C:/Users/me/AppData/Roaming/Concentrator/backups"),
)


class SettingsStack:
    """Renders ``SETTINGS`` into ``renders``; the data file ``DATA_PATH`` is open."""

    def __init__(self, *, attached: bool = True) -> None:
        self.storage = StorageStack()
        self.timer = TimerStack()
        self.timer.catalog.builtin = (*self.timer.catalog.builtin, "chime")
        storage = self.storage
        if attached:
            storage.coordinator.attach(DATA_PATH, SAVED_AT)
        self.dialogs = storage.dialogs
        self.opener = FakeLinkOpener()
        self.recovered: list[StartupPlan] = []
        self.recovery_opens = True
        self.layout_resets = 0
        self.data_commands = DataFileCommands(
            file=storage.file,
            session=storage.session,
            coordinator=storage.coordinator,
            startup=storage.commands,
            preferences=storage.preferences,
        )
        self.files = SettingsFilesPresenter(storage.translator, storage.gate, storage.renderer, self._files_services())
        self.files.add_layout_reset_listener(self._count_layout_reset)
        self.presenter = SettingsPresenter(
            storage.translator, storage.gate, storage.renderer, self._services(), self.files
        )
        self.presenter.attach(self.dialogs)
        storage.bus.subscribe(UserSettingsChangedEvent, self.presenter.on_stored_values_changed)
        self.timer.bus.subscribe(HourlyChimeChangedEvent, self.presenter.on_stored_values_changed)
        self.renders: list[SettingsSnapshot] = []
        storage.renderer.register(RenderSectionEnum.SETTINGS, self.presenter.build_snapshot, self.renders.append)

    @property
    def last(self) -> SettingsSnapshot:
        return self.renders[-1]

    def render(self) -> SettingsSnapshot:
        self.storage.renderer.request(RenderSectionEnum.SETTINGS)
        self.storage.scheduler.run_pending()
        return self.last

    def click(self, action_value: int, *, files: bool = False) -> None:
        self.storage.after_cooldown()
        handler = self.files if files else self.presenter
        handler.on_action_requested(action_value)
        self.storage.scheduler.run_pending()

    def _services(self) -> SettingsServices:
        return SettingsServices(
            settings_queries=SettingsQueries(self.storage.settings),
            settings_commands=SettingsCommands(
                self.storage.settings, self.storage.settings, self.storage.clock, self.storage.bus
            ),
            defaults=SETTINGS_DEFAULTS,
            chime_queries=self.timer.chime_queries,
            chime_commands=self.timer.chime_commands,
            sounds=self.timer.queries,
            preview=self.timer.preview,
            switcher=self.storage.switcher,
        )

    def _files_services(self) -> SettingsFilesServices:
        flow = DataFileFlow(
            self.storage.translator,
            DataFileServices(
                commands=self.data_commands,
                settings=SettingsQueries(self.storage.settings),
                switcher=self.storage.switcher,
                recovery=self._recover,
            ),
        )
        return SettingsFilesServices(
            data_file=flow,
            current_path=lambda: self.data_commands.current_path,
            opener=self.opener,
            layout=LayoutStateKeeper(self.storage.preferences),
            about=ABOUT,
        )

    def _recover(self, plan: StartupPlan) -> bool:
        self.recovered.append(plan)
        return self.recovery_opens

    def _count_layout_reset(self) -> None:
        self.layout_resets += 1
