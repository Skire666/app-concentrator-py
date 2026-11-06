"""A real ``MainWindow`` wired to the real presenters, with fake ports."""

from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.windows.main_window import MainWindow
from tests.fakes.app_config_factory import make_app_config
from tests.fakes.fake_clock import FakeClock
from tests.fakes.fake_translator import FakeTranslator
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.manual_scheduler import ManualScheduler


class ShellHarness:
    """Builds the window; ``turn()`` runs the pending event-loop work of the manual scheduler."""

    def __init__(self, preferences: InMemoryViewPreferences | None = None, module_bar_width_px: int = 100) -> None:
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
        self.translator = FakeTranslator()
        self.scheduler = ManualScheduler()
        self.preferences = preferences or InMemoryViewPreferences()
        renderer = RenderCoordinator(self.scheduler)
        gate = ActionGate(FakeClock(), self.scheduler, renderer, cooldown_ms=100, slow_threshold_ms=200)
        self.presenter = ShellPresenter(self.translator, gate, renderer)
        paths = AppPaths.from_runtime()
        self.window = MainWindow(
            presenter=self.presenter,
            renderer=renderer,
            layout_keeper=LayoutStateKeeper(self.preferences),
            shell_layout=self.layout,
            icons=IconLoader(paths.icons_dir),
            app_icon=IconLoader(paths.icons_dir).icon("concentrator.ico"),
        )
        renderer.request_all()
        renderer.flush()

    def turn(self) -> None:
        self.scheduler.run_pending()
