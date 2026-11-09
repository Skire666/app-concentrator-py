"""Special options block of zone 2: the "Chime every hour" check box and its "..." button."""

import logging
from collections.abc import Callable

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.chime_commands import ChimeCommands
from concentrator.application.timer.chime_queries import ChimeQueries
from concentrator.application.timer.timer_events import HourlyChimeChangedEvent
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.timer.chime_hours import hour_text
from concentrator.presentation.timer.chime_settings_snapshot import SpecialOptionsSnapshot

_logger = logging.getLogger(__name__)


class ChimePresenter:
    """Builds ``SPECIAL_OPTIONS``; the check box switches the chime, "..." opens the chime dialog."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        queries: ChimeQueries,
        commands: ChimeCommands,
        open_editor: Callable[[], ValidationResult],
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            queries: Stored switch and hours.
            commands: Switches the chime.
            open_editor: Shows the chime dialog modally.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._queries = queries
        self._operations: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.CHIME_TOGGLE: lambda: commands.set_enabled(not queries.enabled()),
            ActionIdEnum.CHIME_EDIT: open_editor,
        }

    def build_snapshot(self) -> SpecialOptionsSnapshot:
        """Describe the special options now.

        Returns:
            The snapshot.
        """
        settings = self._queries.settings()
        start, end = (hour_text(self._translator, hour) for hour in (settings.start_hour, settings.end_hour))
        return SpecialOptionsSnapshot(
            title=self._translator.tr("special_options.title"),
            chime=action_button(self._texts, self._gate, ActionIdEnum.CHIME_TOGGLE, checked=self._queries.enabled()),
            chime_hours=self._translator.tr("chime.hours", start=start, end=end),
            chime_edit=action_button(self._texts, self._gate, ActionIdEnum.CHIME_EDIT),
        )

    def on_chime_changed(self, _event: HourlyChimeChangedEvent) -> None:
        """Re-render after the chime changed.

        Args:
            _event: Published by the chime use cases.
        """
        self._renderer.request(RenderSectionEnum.SPECIAL_OPTIONS)

    def on_action_requested(self, action_value: int) -> None:
        """Handle the check box and the "..." button.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._operations.get(action)
        if operation is None:
            _logger.warning("Special options action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=action is ActionIdEnum.CHIME_EDIT)
        if result.is_failure:
            _logger.warning("Special options action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.SPECIAL_OPTIONS)
