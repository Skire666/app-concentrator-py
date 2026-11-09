"""A real ``MainWindow`` wired to the real presenters, with fake ports."""

from concentrator.application.timer.timer_events import TimerChangedEvent, TimerConfigChangedEvent
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.main_window_presenters import MainWindowPresenters
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from concentrator.presentation.timer.timer_layout import TimerLayout
from concentrator.presentation.timer.timer_presenter import TimerPresenter
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.windows.main_window import MainWindow
from tests.fakes.app_config_factory import make_app_config
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.storage_stack import StorageStack
from tests.fakes.timer_factory import LIMITS
from tests.fakes.timer_stack import BLINK_MS, TimerStack
from tests.fakes.timer_ui_stack import FakeTimerEditDialog


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
        self.presenter = ShellPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            lambda: self.timer.queries.current_view().state is TimerStateEnum.RINGING,
        )
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
        self.editor = TimerEditPresenter(
            self.translator,
            self.stack.gate,
            self.stack.renderer,
            self.timer.queries,
            self.timer.commands,
            self.timer.preview,
            LIMITS,
        )
        self.editor.attach(FakeTimerEditDialog(), self.stack.dialogs)
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
        paths = AppPaths.from_runtime()
        self.window = MainWindow(
            presenters=MainWindowPresenters(
                shell=self.presenter, status_bar=self.status_bar, shutdown=self.shutdown, timer=self.timer_presenter
            ),
            renderer=self.stack.renderer,
            layout_keeper=LayoutStateKeeper(self.preferences),
            shell_layout=self.layout,
            timer_layout=TimerLayout.from_ui_section(config.ui),
            icons=IconLoader(paths.icons_dir),
            app_icon=IconLoader(paths.icons_dir).icon("concentrator.ico"),
        )
        self.stack.renderer.request_all()
        self.stack.renderer.flush()

    def turn(self) -> None:
        self.scheduler.run_pending()
