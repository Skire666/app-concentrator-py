"""Status bar: save state, unguarded single-instance indicator, language button."""

import logging
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.language_switcher import LanguageSwitcher
from concentrator.presentation.shell.shell_snapshot import StatusBarSnapshot
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts

_logger = logging.getLogger(__name__)

_LANGUAGE_TEXTS: Final = MappingProxyType(
    {
        LanguageEnum.ENGLISH: ("shell.language.button.en", "shell.language.tooltip.en"),
        LanguageEnum.FRENCH: ("shell.language.button.fr", "shell.language.tooltip.fr"),
    }
)


class StatusBarPresenter:
    """Builds the ``STATUS_BAR`` snapshot and handles the language button."""

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        *,
        switcher: LanguageSwitcher,
        save_texts: SaveStatusTexts,
        coordinator: SaveCoordinator,
        instance: InstanceProtectionPresenter,
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs the language toggle.
            renderer: Receives the render requests.
            switcher: Stores and applies the language.
            save_texts: Describes the save state.
            coordinator: Source of the save state.
            instance: Unguarded single-instance indicator.
        """
        self._translator = translator
        self._gate = gate
        self._renderer = renderer
        self._switcher = switcher
        self._save_texts = save_texts
        self._coordinator = coordinator
        self._instance = instance

    def build_snapshot(self) -> StatusBarSnapshot:
        """Describe the status bar.

        Returns:
            The snapshot.
        """
        save = self._save_texts.describe(self._coordinator.status)
        text_key, tooltip_key = _LANGUAGE_TEXTS.get(self._translator.language, _LANGUAGE_TEXTS[LanguageEnum.ENGLISH])
        action = ActionIdEnum.SHELL_TOGGLE_LANGUAGE
        return StatusBarSnapshot(
            save_state_text=save.text,
            save_state_tooltip=save.tooltip,
            instance_warning_text=self._instance.status_text(),
            instance_warning_tooltip=self._instance.status_tooltip(),
            language_button=ButtonSnapshot(
                text=self._translator.tr(text_key),
                tooltip=self._translator.tr(tooltip_key),
                enabled=not self._gate.is_busy(action),
                visible=True,
                action=action,
            ),
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle a click of the status bar.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        if action is not ActionIdEnum.SHELL_TOGGLE_LANGUAGE:
            _logger.warning("Status bar action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, self._switcher.toggle)
        if result.is_failure:
            _logger.warning("Language toggle failed: %s", [code.name for code in result.error_codes])

    def on_save_status_changed(self, _status: SaveStatusChangedEvent) -> None:
        """Re-render the save state (subscribed to ``SaveStatusChangedEvent``).

        Args:
            _status: New status (read again from the coordinator when building).
        """
        self._renderer.request(RenderSectionEnum.STATUS_BAR)
