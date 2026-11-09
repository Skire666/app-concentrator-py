"""Favorites panel: one button per favorite, its context menu and the "Add..." button."""

import logging
from collections.abc import Callable
from dataclasses import replace
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.preset_commands import PresetCommands
from concentrator.application.timer.preset_queries import PresetQueries
from concentrator.application.timer.timer_events import TimerChangedEvent, TimerPresetsChangedEvent
from concentrator.application.timer.timer_queries import TimerQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.timer_preset import TimerPreset
from concentrator.domain.timer.timer_preset_rules import TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.timer.timer_state_enum import TimerStateEnum
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.duration_label_formatter import DurationLabelFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.timer.preset_edit_presenter import PresetEditPresenter
from concentrator.presentation.timer.presets_snapshot import PresetSnapshot, PresetsSnapshot

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "PresetsPresenter.attach() was not called"
INTERACTIVE_ACTIONS: Final = frozenset({ActionIdEnum.PRESET_ADD, ActionIdEnum.PRESET_EDIT, ActionIdEnum.PRESET_DELETE})
MENU_ACTIONS: Final = (ActionIdEnum.PRESET_EDIT, ActionIdEnum.PRESET_DELETE)

type PresetOperation = Callable[[str], ValidationResult]
"""A context menu or button action on one favorite."""


class PresetsPresenter:
    """Builds ``PRESETS`` and runs the favorite actions through the action gate.

    The favorites are always enabled: a click replaces a countdown in progress. Their tooltip follows the
    timer state, so the panel re-renders on timer transitions only, not on every displayed second.
    Favorites are not moved (owner decision at the phase 3 review): a new one goes last.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        queries: PresetQueries,
        timer: TimerQueries,
        commands: PresetCommands,
        editor: PresetEditPresenter,
    ) -> None:
        """Create the presenter; the dialog service comes with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Favorites and their limit.
            timer: Timer state.
            commands: Favorite use cases.
            editor: Opens the favorite dialog.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._labels = DurationLabelFormatter(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._timer = timer
        self._commands = commands
        self._editor = editor
        self._dialogs: DialogPort | None = None
        self._operations: dict[ActionIdEnum, PresetOperation] = {
            ActionIdEnum.PRESET_APPLY: commands.apply_and_start,
            ActionIdEnum.PRESET_EDIT: editor.open_edit,
            ActionIdEnum.PRESET_DELETE: self._delete,
        }

    def attach(self, dialogs: DialogPort) -> None:
        """Set the dialog service (built with the main window).

        Args:
            dialogs: Delete confirmation over the main window (ADR-036).
        """
        self._dialogs = dialogs

    def build_snapshot(self) -> PresetsSnapshot:
        """Describe the favorites panel now (the favorites are read once).

        Returns:
            The snapshot.
        """
        presets = self._queries.presets()
        idle = self._timer.current_view().state is TimerStateEnum.IDLE
        return PresetsSnapshot(
            title=self._translator.tr("presets.title"),
            presets=tuple(self._preset(preset, idle=idle) for preset in presets),
            add=self._add_button(presets),
            empty_text="" if presets.items else self._translator.tr("presets.empty"),
        )

    def label(self, preset: TimerPreset) -> str:
        """Return the text of a favorite: its label, or the automatic one.

        Args:
            preset: Favorite.

        Returns:
            The text.
        """
        return preset.label or self._labels.label(preset.duration)

    def on_timer_changed(self, event: TimerChangedEvent) -> None:
        """Re-render when the timer changes state (not on every displayed second).

        Args:
            event: Published by the timer engine.
        """
        if event.transitions:
            self._renderer.request(RenderSectionEnum.PRESETS)

    def on_presets_changed(self, _event: TimerPresetsChangedEvent) -> None:
        """Re-render after a favorite changed.

        Args:
            _event: Published by the favorite use cases.
        """
        self._renderer.request(RenderSectionEnum.PRESETS)

    def on_action_requested(self, action_value: int) -> None:
        """Handle the "Add..." button.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        if action is not ActionIdEnum.PRESET_ADD:
            _logger.warning("Favorites action %s (%d) is not handled", action.name, action_value)
            return
        self._run(action, self._editor.open_new)

    def on_preset_action_requested(self, action_value: int, preset_id: str) -> None:
        """Handle a click on a favorite or an item of its context menu.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
            preset_id: Favorite concerned.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._operations.get(action)
        if operation is None:
            _logger.warning("Favorite action %s (%d) is not handled", action.name, action_value)
            return
        self._run(action, lambda: operation(preset_id))

    def _run(self, action: ActionIdEnum, operation: Callable[[], ValidationResult]) -> None:
        """Run an action through the gate and re-render.

        Args:
            action: Action.
            operation: The work.
        """
        result = self._gate.run(action, operation, interactive=action in INTERACTIVE_ACTIONS)
        if result.is_failure:
            _logger.warning("Favorite action %s failed: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.PRESETS)

    def _delete(self, preset_id: str) -> ValidationResult:
        """Ask for confirmation, then delete a favorite.

        Args:
            preset_id: Favorite to delete.

        Returns:
            Success, skipped when the user said no, or ``ENTITY_NOT_FOUND``.
        """
        preset = self._queries.preset(preset_id)
        if preset.data is None:
            return preset.validation
        tr = self._translator.tr
        confirmed = self._attached_dialogs().confirm(
            tr("presets.delete.title"),
            tr("presets.delete.message", label=self.label(preset.data)),
            tr("presets.delete.accept"),
            tr("dialog.button.cancel"),
        )
        if not confirmed:
            return ValidationResult.skipped()
        return self._commands.delete(preset_id)

    def _preset(self, preset: TimerPreset, *, idle: bool) -> PresetSnapshot:
        """Describe one favorite.

        Args:
            preset: Favorite.
            idle: Whether the timer is idle (otherwise the button replaces the countdown).

        Returns:
            The favorite snapshot.
        """
        key = "presets.tooltip.start" if idle else "presets.tooltip.replace"
        button = ButtonSnapshot(
            text=self.label(preset),
            tooltip=self._translator.tr(key, duration=preset.duration.as_clock_text()),
            enabled=not self._gate.is_busy(ActionIdEnum.PRESET_APPLY),
            visible=True,
            action=ActionIdEnum.PRESET_APPLY,
        )
        menu = tuple(action_button(self._texts, self._gate, action) for action in MENU_ACTIONS)
        return PresetSnapshot(preset_id=preset.id, button=button, menu=menu)

    def _add_button(self, presets: TimerPresetsCollection) -> ButtonSnapshot:
        """Describe the "Add..." button.

        Args:
            presets: Current favorites.

        Returns:
            The button, disabled with the limit as tooltip when the favorites are full.
        """
        limits = self._queries.limits
        room = TimerPresetRules.validate_room(presets, limits).is_success
        button = action_button(self._texts, self._gate, ActionIdEnum.PRESET_ADD, enabled=room)
        if room:
            return button
        return replace(button, tooltip=self._translator.tr("error.preset_limit_reached", max=limits.max_presets))

    def _attached_dialogs(self) -> DialogPort:
        """The dialog service.

        Returns:
            The service given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._dialogs is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._dialogs
