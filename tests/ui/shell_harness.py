"""A real ``MainWindow`` wired to the real presenters, with fake ports."""

from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.shell_layout import ShellLayout
from concentrator.presentation.shell.shell_presenter import ShellPresenter
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from concentrator.presentation.storage.shutdown_presenter import ShutdownPresenter
from concentrator.ui.support.icon_loader import IconLoader
from concentrator.ui.windows.main_window import MainWindow
from tests.fakes.app_config_factory import make_app_config
from tests.fakes.in_memory_view_preferences import InMemoryViewPreferences
from tests.fakes.storage_stack import StorageStack


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
        self.presenter = ShellPresenter(self.translator, self.stack.gate, self.stack.renderer)
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
        paths = AppPaths.from_runtime()
        self.window = MainWindow(
            presenter=self.presenter,
            status_bar=self.status_bar,
            shutdown=self.shutdown,
            renderer=self.stack.renderer,
            layout_keeper=LayoutStateKeeper(self.preferences),
            shell_layout=self.layout,
            icons=IconLoader(paths.icons_dir),
            app_icon=IconLoader(paths.icons_dir).icon("concentrator.ico"),
        )
        self.stack.renderer.request_all()
        self.stack.renderer.flush()

    def turn(self) -> None:
        self.scheduler.run_pending()
