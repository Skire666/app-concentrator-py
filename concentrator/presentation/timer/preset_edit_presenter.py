"""Favorite dialog: label and duration of a new or existing favorite."""

import logging
from collections.abc import Callable
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.preset_commands import PresetCommands
from concentrator.application.timer.preset_queries import PresetQueries
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import SECONDS_PER_HOUR, Duration
from concentrator.domain.timer.timer_config_rules import DURATION_FIELD
from concentrator.domain.timer.timer_preset import BLOCKED_LABEL_CHARACTERS
from concentrator.domain.timer.timer_preset_rules import LABEL_FIELD
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.duration_label_formatter import DurationLabelFormatter
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.editor_dialog_port import EditorDialogPort
from concentrator.presentation.timer.preset_edit_form import PresetDraft, PresetEditForm
from concentrator.presentation.timer.preset_edit_snapshot import LabelInputSnapshot, PresetEditSnapshot
from concentrator.presentation.timer.timer_edit_snapshot import DurationInputSnapshot

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "PresetEditPresenter.attach() was not called"
NEW_PRESET: Final = PresetDraft(label="", duration=Duration(0))


class PresetEditPresenter:
    """Owns the favorite form while the dialog is open; builds ``PRESET_EDIT`` and handles its buttons.

    Cancel, Escape and the close button close the dialog without asking (owner decision, ADR-038).
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        queries: PresetQueries,
        commands: PresetCommands,
    ) -> None:
        """Create the presenter; the dialog comes with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Favorites and their limits.
            commands: Stores the favorite.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._labels = DurationLabelFormatter(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._commands = commands
        self._window: EditorDialogPort | None = None
        self._form: PresetEditForm | None = None
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.PRESET_EDIT_SAVE: self._save,
            ActionIdEnum.PRESET_EDIT_CANCEL: self._cancel,
        }

    def attach(self, window: EditorDialogPort) -> None:
        """Set the dialog (built with the main window).

        Args:
            window: The favorite dialog.
        """
        self._window = window

    def open_new(self) -> ValidationResult:
        """Add a favorite: empty label, duration 00:00:00 (``PRESET_ADD``, owner decision at the review).

        Returns:
            Success once the dialog closed.
        """
        return self._open(NEW_PRESET, preset_id="")

    def open_edit(self, preset_id: str) -> ValidationResult:
        """Edit a favorite (``PRESET_EDIT``).

        Args:
            preset_id: Favorite to edit.

        Returns:
            Success once the dialog closed, or ``ENTITY_NOT_FOUND``.
        """
        preset = self._queries.preset(preset_id)
        if preset.data is None:
            return preset.validation
        return self._open(PresetDraft(label=preset.data.label, duration=preset.data.duration), preset_id=preset_id)

    def build_snapshot(self) -> PresetEditSnapshot:
        """Describe the dialog.

        Returns:
            The snapshot of the draft (of a new favorite before the first opening).
        """
        tr = self._translator.tr
        form = self._current_form()
        return PresetEditSnapshot(
            title=tr("preset.edit.title.new") if form.is_new else tr("preset.edit.title.edit"),
            label=LabelInputSnapshot(
                label=tr("preset.edit.label"),
                text=form.draft.label,
                placeholder=self._placeholder(form),
                blocked_characters=BLOCKED_LABEL_CHARACTERS,
                error=self._error(form, LABEL_FIELD),
            ),
            duration=self._duration_input(form),
            save=action_button(self._texts, self._gate, ActionIdEnum.PRESET_EDIT_SAVE, enabled=form.can_submit),
            cancel=action_button(self._texts, self._gate, ActionIdEnum.PRESET_EDIT_CANCEL),
        )

    def on_label_changed(self, text: str) -> None:
        """Handle a change of the label field.

        Args:
            text: Label as typed.
        """
        self._current_form().set_label(text)
        self._renderer.request(RenderSectionEnum.PRESET_EDIT)

    def on_duration_changed(self, hours: int, minutes: int, seconds: int) -> None:
        """Handle a change of the duration fields.

        Args:
            hours: Hours.
            minutes: Minutes.
            seconds: Seconds.
        """
        self._current_form().set_duration(hours, minutes, seconds)
        self._renderer.request(RenderSectionEnum.PRESET_EDIT)

    def on_action_requested(self, action_value: int) -> None:
        """Handle a button of the dialog.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Favorite dialog action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation)
        if result.is_failure:
            _logger.warning("Favorite dialog action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.PRESET_EDIT)

    def _open(self, draft: PresetDraft, *, preset_id: str) -> ValidationResult:
        """Show the dialog on a draft.

        Args:
            draft: Values shown first.
            preset_id: Favorite being edited, ``""`` for a new one.

        Returns:
            Success once the dialog closed.
        """
        self._form = PresetEditForm(
            draft, limits=self._queries.limits, presets=self._queries.presets(), preset_id=preset_id
        )
        self._attached_window().show_editor()
        return ValidationResult.success()

    def _save(self) -> ValidationResult:
        """Store the draft and close the dialog.

        Returns:
            Success, skipped when there is nothing valid to save, or the failure (the dialog stays open).
        """
        form = self._current_form()
        if not form.can_submit:
            return ValidationResult.skipped()
        draft = form.draft
        if form.is_new:
            result = self._commands.create(draft.label, draft.duration).validation
        else:
            result = self._commands.update(form.preset_id, draft.label, draft.duration).validation
        if result.is_failure:
            return result
        self._attached_window().close_editor()
        return result

    def _cancel(self) -> ValidationResult:
        """Close the dialog without saving and without asking (ADR-038).

        Returns:
            Success.
        """
        self._attached_window().close_editor()
        return ValidationResult.success()

    def _duration_input(self, form: PresetEditForm) -> DurationInputSnapshot:
        """Describe the duration field.

        Args:
            form: Current form.

        Returns:
            The field snapshot.
        """
        tr = self._translator.tr
        hours, minutes, seconds = form.draft.duration.hms
        return DurationInputSnapshot(
            label=tr("preset.edit.duration"),
            hours=hours,
            minutes=minutes,
            seconds=seconds,
            max_hours=self._queries.limits.max_duration_seconds // SECONDS_PER_HOUR,
            hours_unit=tr("timer.edit.unit.hours"),
            minutes_unit=tr("timer.edit.unit.minutes"),
            seconds_unit=tr("timer.edit.unit.seconds"),
            error=self._error(form, DURATION_FIELD),
        )

    def _placeholder(self, form: PresetEditForm) -> str:
        """Return the automatic label shown in the empty label field.

        Args:
            form: Current form.

        Returns:
            "Automatic: 25 min", ``""`` while the duration is 00:00:00.
        """
        duration = form.draft.duration
        if not duration.seconds:
            return ""
        return self._translator.tr("preset.edit.label_placeholder", label=self._labels.label(duration))

    def _error(self, form: PresetEditForm, field: str) -> str:
        """Return the inline message of a field.

        Args:
            form: Current form.
            field: Field path of the rules.

        Returns:
            The first message, ``""`` when the field is valid or the errors are not shown yet.
        """
        issues = form.errors.issues_for(field) if form.shows_errors else ()
        return self._texts.issue_message(issues[0]) if issues else ""

    def _current_form(self) -> PresetEditForm:
        """Return the form being edited, a new favorite if none is open.

        Returns:
            The form.
        """
        if self._form is None:
            self._form = PresetEditForm(
                NEW_PRESET, limits=self._queries.limits, presets=self._queries.presets(), preset_id=""
            )
        return self._form

    def _attached_window(self) -> EditorDialogPort:
        """The dialog.

        Returns:
            The dialog given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._window is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._window
