"""A real ``MainWindow`` wired to the real presenters, with fake ports."""

from concentrator.application.timer.timer_events import (
    HourlyChimeChangedEvent,
    TimerChangedEvent,
    TimerConfigChangedEvent,
    TimerPresetsChangedEvent,
)
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.journal.journal_layout import JournalLayout
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.shell.window_layouts import WindowLayouts
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.chime_presenter import ChimePresenter
from concentrator.presentation.timer.chime_settings_presenter import ChimeSettingsPresenter
from concentrator.presentation.timer.preset_edit_presenter import PresetEditPresenter
from concentrator.presentation.timer.presets_presenter import PresetsPresenter
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.timer.timer_presenter import TimerPresenter
from concentrator.presentation.todo.todo_layout import TodoLayout
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.windows.main_window import MainWindow
from tests.fakes.app_config_factory import make_app_config
from tests.fakes.focus_ui_stack import FocusUiStack
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.journal_stack import JournalStack
from tests.fakes.settings_stack import SettingsStack
from tests.fakes.storage_stack import StorageStack
from tests.fakes.timer_factory import LIMITS
from tests.fakes.timer_stack import BLINK_MS, TimerStack
from tests.fakes.timer_ui_stack import FakeEditorDialog
from tests.fakes.todo_ui_stack import SharedUi


class ShellHarness:
    """Builds the window; ``turn()`` runs the pending event-loop work of the manual scheduler."""

    def __init__(
        self,
        preferences: InMemoryViewPreferences | None = None,
        module_bar_width_px: int = 100,
        *,
        protected: bool = True,
    ) -> None:
        config = make_app_config()
        self.layout = ShellLayout.from_ui_section(config.ui)
        self.layout = ShellLayout(
            module_bar_width_px=module_bar_width_px,
            zone1_ratio_percent=self.layout.zone1_ratio_percent,
            default_width_px=self.layout.default_width_px,
            default_height_px=self.layout.default_height_px,
            min_width_px=self.layout.min_width_px,
            min_height_px=self.layout.min_height_px,
        )
        self.stack = StorageStack()
        if preferences is not None:
            self.stack.preferences = preferences
        self.translator = self.stack.translator
        self.scheduler = self.stack.scheduler
        self.preferences = self.stack.preferences
        self.timer = TimerStack()
        self.journal = JournalStack()
        self.journal_presenter = self.journal.rewire(
            self.translator, self.stack.gate, self.stack.renderer, (self.scheduler, self.preferences)
        )
        self.presenter = ShellPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            lambda: self.timer.queries.current_view().state is TimerStateEnum.RINGING,
            journal_badge=self.journal_presenter.badge_count,
        )
        self.presenter.add_page_listener(self.journal_presenter.on_page_changed)
        self.settings = SettingsStack(attached=False, stacks=(self.stack, self.timer), register=False)
        self.presenter.add_page_listener(self.settings.presenter.on_page_changed)
        self.presenter.set_leave_guard(ShellPageEnum.SETTINGS, self.settings.presenter.may_leave)
        self.status_bar = StatusBarPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            switcher=self.stack.switcher,
            save_texts=SaveStatusTexts(self.translator, self.stack.formatter),
            coordinator=self.stack.coordinator,
            instance=InstanceProtectionPresenter(self.translator, protected=protected),
        )
        self.shutdown = ShutdownPresenter(self.stack.coordinator, self.translator)
        self.shutdown.attach(self.stack.dialogs)
        self.shutdown.watch_edits(self.settings.presenter)
        self.editor = TimerEditPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            self.timer.queries,
            self.timer.commands,
            self.timer.preview,
            LIMITS,
        )
        self.editor.attach(FakeEditorDialog(), self.stack.dialogs)
        self.timer_presenter = TimerPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            self.timer.queries,
            self.timer.commands,
            DateTimeFormatter(self.translator, self.stack.clock),
            self.editor.open,
            BLINK_MS,
        )
        self.timer.bus.subscribe(TimerChangedEvent, self.timer_presenter.on_timer_changed)
        self.timer.bus.subscribe(TimerConfigChangedEvent, self.timer_presenter.on_config_changed)
        self.timer.bus.subscribe(TimerChangedEvent, self.presenter.on_timer_changed)
        self._build_timer_extras()
        self.todo = FocusUiStack(
            shared=SharedUi(
                translator=self.translator,
                scheduler=self.scheduler,
                renderer=self.stack.renderer,
                gate=self.stack.gate,
                dialogs=self.stack.dialogs,
                preferences=self.preferences,
            )
        )
        paths = AppPaths.from_runtime()
        self.window = MainWindow(
            presenters=MainWindowPresenters(
                shell=self.presenter,
                status_bar=self.status_bar,
                shutdown=self.shutdown,
                timer=self.timer_presenter,
                presets=self.presets,
                chime=self.chime,
                journal=self.journal_presenter,
                settings=self.settings.presenter,
                settings_files=self.settings.files,
                todo=self.todo.presenters(),
                focus=self.todo.focus_presenters(),
            ),
            renderer=self.stack.renderer,
            layout_keeper=LayoutStateKeeper(self.preferences),
            layouts=WindowLayouts(
                shell=self.layout,
                timer=TimerLayout.from_ui_section(config.ui),
                journal=JournalLayout.from_journal_section(config.journal),
                todo=TodoLayout.from_config(config),
            ),
            icons=IconLoader(paths.icons_dir),
            app_icon=IconLoader(paths.icons_dir).icon("concentrator.ico"),
        )
        self.stack.renderer.request_all()
        self.stack.renderer.flush()

    def _build_timer_extras(self) -> None:
        """Favorites and special options presenters on the timer stack, as bootstrap wires them."""
        timer, gate, renderer = self.timer, self.stack.gate, self.stack.renderer
        self.preset_window = FakeEditorDialog()
        self.preset_editor = PresetEditPresenter(
            self.translator, gate, renderer, timer.preset_queries, timer.preset_commands
        )
        self.preset_editor.attach(self.preset_window)
        self.presets = PresetsPresenter(
            self.translator,
            gate,
            renderer,
            queries=timer.preset_queries,
            timer=timer.queries,
            commands=timer.preset_commands,
            editor=self.preset_editor,
        )
        self.presets.attach(self.stack.dialogs)
        self.chime_window = FakeEditorDialog()
        self.chime_editor = ChimeSettingsPresenter(
            self.translator,
            gate,
            renderer,
            queries=timer.chime_queries,
            commands=timer.chime_commands,
            sounds=timer.queries,
            preview=timer.preview,
        )
        self.chime_editor.attach(self.chime_window, self.stack.dialogs)
        self.chime = ChimePresenter(
            self.translator, gate, renderer, timer.chime_queries, timer.chime_commands, self.chime_editor.open
        )
        timer.bus.subscribe(TimerChangedEvent, self.presets.on_timer_changed)
        timer.bus.subscribe(TimerPresetsChangedEvent, self.presets.on_presets_changed)
        timer.bus.subscribe(HourlyChimeChangedEvent, self.chime.on_chime_changed)

    def turn(self) -> None:
        self.scheduler.run_pending()
