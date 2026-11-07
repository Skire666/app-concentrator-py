"""Page switching and window title of the window shell (the status bar has its own presenter)."""

import logging
from itertools import starmap
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from concentrator.presentation.shell.shell_snapshot import ModuleButtonSnapshot, ShellSnapshot

_logger = logging.getLogger(__name__)

PAGE_ACTIONS: Final = MappingProxyType(
    {
        ActionIdEnum.SHELL_SHOW_FOCUS: ShellPageEnum.FOCUS,
        ActionIdEnum.SHELL_SHOW_JOURNAL: ShellPageEnum.JOURNAL,
        ActionIdEnum.SHELL_SHOW_SETTINGS: ShellPageEnum.SETTINGS,
    }
)
PAGE_ORDER: Final = tuple(PAGE_ACTIONS.values())


class ShellPresenter:
    """Builds the ``SHELL`` snapshot and handles the module bar actions."""

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

    def on_action_requested(self, action_value: int) -> None:
        """Handle a click of the module bar.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        page = PAGE_ACTIONS.get(action)
        if page is None:
            _logger.warning("Shell action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, lambda: self._show_page(page))
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
