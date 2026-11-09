"""Timer presenters on top of ``TimerStack``, with a gate, a renderer and scripted dialogs."""

from collections.abc import Callable
from typing import Final, override

from concentrator.application.timer.timer_events import (
    HourlyChimeChangedEvent,
    TimerChangedEvent,
    TimerConfigChangedEvent,
    TimerPresetsChangedEvent,
)
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.timer.timer_settings import TimerSettings
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.chime_presenter import ChimePresenter
from concentrator.presentation.timer.chime_settings_presenter import ChimeSettingsPresenter
from concentrator.presentation.timer.chime_settings_snapshot import ChimeSettingsSnapshot, SpecialOptionsSnapshot
from concentrator.presentation.timer.preset_edit_presenter import PresetEditPresenter
from concentrator.presentation.timer.preset_edit_snapshot import PresetEditSnapshot
from concentrator.presentation.timer.presets_presenter import PresetsPresenter
from concentrator.presentation.timer.presets_snapshot import PresetsSnapshot
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
        self._build_extra_presenters(register_editors=register_editor)

    def _build_extra_presenters(self, *, register_editors: bool) -> None:
        """Favorites, favorite dialog, special options and chime dialog, with recorded renders."""
        self.preset_window = FakeEditorDialog()
        self.preset_editor = PresetEditPresenter(
            self.translator, self.gate, self.renderer, self.preset_queries, self.preset_commands
        )
        self.preset_editor.attach(self.preset_window)
        self.presets_presenter = PresetsPresenter(
            self.translator,
            self.gate,
            self.renderer,
            queries=self.preset_queries,
            timer=self.queries,
            commands=self.preset_commands,
            editor=self.preset_editor,
        )
        self.presets_presenter.attach(self.dialogs)
        self.chime_window = FakeEditorDialog()
        self.chime_editor = ChimeSettingsPresenter(
            self.translator,
            self.gate,
            self.renderer,
            queries=self.chime_queries,
            commands=self.chime_commands,
            sounds=self.queries,
            preview=self.preview,
        )
        self.chime_editor.attach(self.chime_window, self.dialogs)
        self.chime_presenter = ChimePresenter(
            self.translator, self.gate, self.renderer, self.chime_queries, self.chime_commands, self.chime_editor.open
        )
        self.preset_renders: list[PresetsSnapshot] = []
        self.preset_edit_renders: list[PresetEditSnapshot] = []
        self.options_renders: list[SpecialOptionsSnapshot] = []
        self.chime_edit_renders: list[ChimeSettingsSnapshot] = []
        register = self.renderer.register
        register(RenderSectionEnum.PRESETS, self.presets_presenter.build_snapshot, self.preset_renders.append)
        register(RenderSectionEnum.SPECIAL_OPTIONS, self.chime_presenter.build_snapshot, self.options_renders.append)
        if register_editors:
            register(RenderSectionEnum.PRESET_EDIT, self.preset_editor.build_snapshot, self.preset_edit_renders.append)
            register(RenderSectionEnum.CHIME_EDIT, self.chime_editor.build_snapshot, self.chime_edit_renders.append)
        self.bus.subscribe(TimerChangedEvent, self.presets_presenter.on_timer_changed)
        self.bus.subscribe(TimerPresetsChangedEvent, self.presets_presenter.on_presets_changed)
        self.bus.subscribe(HourlyChimeChangedEvent, self.chime_presenter.on_chime_changed)

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

    @property
    def presets_snapshot(self) -> PresetsSnapshot:
        return self.presets_presenter.build_snapshot()

    def preset_action(self, action: ActionIdEnum, preset_id: str = "") -> None:
        """Wait for the cooldown, then send a favorites panel action (``""``: the Add button)."""
        self.scheduler.advance(COOLDOWN_MS)
        if preset_id:
            self.presets_presenter.on_preset_action_requested(int(action), preset_id)
        else:
            self.presets_presenter.on_action_requested(int(action))

    def preset_edit(self, action: ActionIdEnum) -> None:
        """Wait for the cooldown, then send a favorite dialog action."""
        self.scheduler.advance(COOLDOWN_MS)
        self.preset_editor.on_action_requested(int(action))

    def options_action(self, action: ActionIdEnum) -> None:
        """Wait for the cooldown, then send a special options action."""
        self.scheduler.advance(COOLDOWN_MS)
        self.chime_presenter.on_action_requested(int(action))

    def chime_edit(self, action: ActionIdEnum) -> None:
        """Wait for the cooldown, then send a chime dialog action."""
        self.scheduler.advance(COOLDOWN_MS)
        self.chime_editor.on_action_requested(int(action))
