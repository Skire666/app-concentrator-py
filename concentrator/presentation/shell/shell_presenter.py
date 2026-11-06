"""Page switching, language toggle and status text of the window shell."""

import logging
from itertools import starmap
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_snapshot import ModuleButtonSnapshot, ShellSnapshot, StatusBarSnapshot

_logger = logging.getLogger(__name__)

PAGE_ACTIONS: Final = MappingProxyType(
    {
        ActionIdEnum.SHELL_SHOW_FOCUS: ShellPageEnum.FOCUS,
        ActionIdEnum.SHELL_SHOW_JOURNAL: ShellPageEnum.JOURNAL,
        ActionIdEnum.SHELL_SHOW_SETTINGS: ShellPageEnum.SETTINGS,
    }
)
PAGE_ORDER: Final = tuple(PAGE_ACTIONS.values())
_LANGUAGE_TEXTS: Final = MappingProxyType(
    {
        LanguageEnum.ENGLISH: ("shell.language.button.en", "shell.language.tooltip.en"),
        LanguageEnum.FRENCH: ("shell.language.button.fr", "shell.language.tooltip.fr"),
    }
)
_NEXT_LANGUAGE: Final = MappingProxyType(
    {LanguageEnum.ENGLISH: LanguageEnum.FRENCH, LanguageEnum.FRENCH: LanguageEnum.ENGLISH}
)


class ShellPresenter:
    """Builds the ``SHELL`` and ``STATUS_BAR`` snapshots and handles the shell actions."""

    def __init__(self, translator: TranslatorPort, gate: ActionGate, renderer: RenderCoordinator) -> None:
        """Create the presenter; the Focus page is shown first.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._active_page = ShellPageEnum.FOCUS

    @property
    def active_page(self) -> ShellPageEnum:
        """Page currently shown."""
        return self._active_page

    def build_shell_snapshot(self) -> ShellSnapshot:
        """Describe the window title, the module bar and the pages.

        Returns:
            The snapshot.
        """
        tr = self._translator.tr
        return ShellSnapshot(
            window_title=tr("app.title"),
            module_buttons=tuple(starmap(self._module_button, PAGE_ACTIONS.items())),
            active_page_index=PAGE_ORDER.index(self._active_page),
            focus_zone1_placeholder=tr("placeholder.focus.zone1"),
            focus_zone2_placeholder=tr("placeholder.focus.zone2"),
            journal_placeholder=tr("placeholder.journal"),
            settings_placeholder=tr("placeholder.settings"),
        )

    def build_status_bar_snapshot(self) -> StatusBarSnapshot:
        """Describe the status bar; the language button shows the current language.

        Returns:
            The snapshot.
        """
        text_key, tooltip_key = _LANGUAGE_TEXTS.get(self._translator.language, _LANGUAGE_TEXTS[LanguageEnum.ENGLISH])
        action = ActionIdEnum.SHELL_TOGGLE_LANGUAGE
        language_button = ButtonSnapshot(
            text=self._translator.tr(text_key),
            tooltip=self._translator.tr(tooltip_key),
            enabled=not self._gate.is_busy(action),
            visible=True,
            action=action,
        )
        return StatusBarSnapshot(
            save_state_text=self._translator.tr("status.save.none"), language_button=language_button
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle a click of the module bar or of the status bar.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        page = PAGE_ACTIONS.get(action)
        if page is not None:
            result = self._gate.run(action, lambda: self._show_page(page))
        elif action is ActionIdEnum.SHELL_TOGGLE_LANGUAGE:
            result = self._gate.run(action, self._toggle_language)
        else:
            _logger.warning("Shell action %s (%d) is not handled", action.name, action_value)
            return
        if result.is_failure:
            _logger.warning("Shell action %s failed: %s", action.name, [code.name for code in result.error_codes])

    def _module_button(self, action: ActionIdEnum, page: ShellPageEnum) -> ModuleButtonSnapshot:
        """Describe one module button.

        Args:
            action: Action of the button.
            page: Page it shows.

        Returns:
            The button snapshot.
        """
        return ModuleButtonSnapshot(
            text=self._texts.action_label(action),
            tooltip=self._texts.action_tooltip(action),
            checked=page is self._active_page,
            highlighted=False,
            enabled=not self._gate.is_busy(action),
            action=action,
        )

    def _show_page(self, page: ShellPageEnum) -> ValidationResult:
        """Make a page the visible one.

        Args:
            page: Page to show.

        Returns:
            Success.
        """
        if page is not self._active_page:
            self._active_page = page
            self._renderer.request(RenderSectionEnum.SHELL)
        return ValidationResult.success()

    def _toggle_language(self) -> ValidationResult:
        """Switch between English and French and re-render every section (in memory in phase 0).

        Returns:
            The translator's result.
        """
        language = _NEXT_LANGUAGE.get(self._translator.language, LanguageEnum.ENGLISH)
        result = self._translator.set_language(language)
        if result.is_success:
            _logger.info("UI language switched to %s", language.iso_code)
            self._renderer.request_all()
        return result
