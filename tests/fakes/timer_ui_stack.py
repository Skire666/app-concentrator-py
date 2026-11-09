"""Timer presenters on top of ``TimerStack``, with a gate, a renderer and scripted dialogs."""

from collections.abc import Callable
from typing import Final, override

from concentrator.application.timer.timer_events import TimerChangedEvent, TimerConfigChangedEvent
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.timer_edit_presenter import TimerEditPresenter
from concentrator.presentation.timer.timer_edit_snapshot import TimerEditSnapshot
from concentrator.presentation.timer.timer_presenter import TimerPresenter
from concentrator.presentation.timer.timer_snapshot import TimerSnapshot
from tests.fakes.fake_dialogs import FakeDialogs
from tests.fakes.manual_scheduler import ManualScheduler
from tests.fakes.timer_factory import DEFAULT_SETTINGS, LIMITS
from tests.fakes.timer_stack import BLINK_MS, TimerStack

COOLDOWN_MS: Final = 100


class FakeEditorDialog(EditorDialogPort):
    """``while_open`` runs inside ``show_editor``, as the user would act on the modal dialog."""

    def __init__(self) -> None:
        self.shows = 0
        self.closes = 0
        self.while_open: Callable[[], None] = lambda: None

    @override
    def show_editor(self) -> None:
        self.shows += 1
        self.while_open()

    @override
    def close_editor(self) -> None:
        self.closes += 1


class TimerUiStack(TimerStack):
    """Every collaborator of the timer presenters; rendered snapshots are recorded."""

    def __init__(
        self,
        settings: TimerSettings = DEFAULT_SETTINGS,
        language: LanguageEnum = LanguageEnum.ENGLISH,
        *,
        register_editor: bool = True,
    ) -> None:
        super().__init__(settings, language)
        self.scheduler = ManualScheduler()
        self.renderer = RenderCoordinator(self.scheduler)
        self.gate = ActionGate(
            self.clock, self.scheduler, self.renderer, cooldown_ms=COOLDOWN_MS, slow_threshold_ms=200
        )
        self.dialogs = FakeDialogs()
        self.window = FakeEditorDialog()
        self.editor = TimerEditPresenter(
            self.translator, self.gate, self.renderer, self.queries, self.commands, self.preview, LIMITS
        )
        self.editor.attach(self.window, self.dialogs)
        self.presenter = TimerPresenter(
            self.translator,
            self.gate,
            self.renderer,
            self.queries,
            self.commands,
            DateTimeFormatter(self.translator, self.clock),
            self.editor.open,
            BLINK_MS,
        )
        self.timer_renders: list[TimerSnapshot] = []
        self.edit_renders: list[TimerEditSnapshot] = []
        self.renderer.register(RenderSectionEnum.TIMER, self.presenter.build_snapshot, self.timer_renders.append)
        if register_editor:
            self.renderer.register(RenderSectionEnum.TIMER_EDIT, self.editor.build_snapshot, self.edit_renders.append)
        self.bus.subscribe(TimerChangedEvent, self.presenter.on_timer_changed)
        self.bus.subscribe(TimerConfigChangedEvent, self.presenter.on_config_changed)

    @property
    def snapshot(self) -> TimerSnapshot:
        return self.presenter.build_snapshot()

    @property
    def edit_snapshot(self) -> TimerEditSnapshot:
        return self.editor.build_snapshot()

    def press(self, action: ActionIdEnum) -> None:
        """Send a timer button action without waiting for the cooldown."""
        self.presenter.on_action_requested(int(action))

    def click(self, action: ActionIdEnum) -> None:
        """Wait for the cooldown, then send a timer button action."""
        self.scheduler.advance(COOLDOWN_MS)
        self.press(action)

    def edit(self, action: ActionIdEnum) -> None:
        """Wait for the cooldown, then send an edit dialog action."""
        self.scheduler.advance(COOLDOWN_MS)
        self.editor.on_action_requested(int(action))
