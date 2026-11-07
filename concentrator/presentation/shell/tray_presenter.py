"""Notification area icon: tooltip and the Show / Quit menu."""

import logging
from collections.abc import Callable
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.main_window_port import MainWindowPort
from concentrator.presentation.shell.shell_snapshot import TraySnapshot

_logger = logging.getLogger(__name__)

_NOT_ATTACHED: Final = "TrayPresenter.attach() was not called"


class TrayPresenter:
    """Builds the ``TRAY`` snapshot; a click on the icon or on a notification shows the window."""

    def __init__(self, translator: TranslatorPort, gate: ActionGate) -> None:
        """Create the presenter; the window comes with ``attach``.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._window: MainWindowPort | None = None
        self._actions: dict[ActionIdEnum, tuple[Callable[[], ValidationResult], bool]] = {
            ActionIdEnum.TRAY_SHOW: (self._show, False),
            ActionIdEnum.TRAY_QUIT: (self._quit, True),
        }

    def attach(self, window: MainWindowPort) -> None:
        """Set the main window.

        Args:
            window: Window shown or closed by the menu.
        """
        self._window = window

    def build_snapshot(self) -> TraySnapshot:
        """Describe the icon and its menu.

        Returns:
            The snapshot.
        """
        return TraySnapshot(
            tooltip=self._translator.tr("app.title"),
            show_action=self._item(ActionIdEnum.TRAY_SHOW),
            quit_action=self._item(ActionIdEnum.TRAY_QUIT),
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle a menu item, a click on the icon or on a notification.

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        handler = self._actions.get(action)
        if handler is None:
            _logger.warning("Tray action %s (%d) is not handled", action.name, action_value)
            return
        operation, interactive = handler
        self._gate.run(action, operation, interactive=interactive)

    def _item(self, action: ActionIdEnum) -> ButtonSnapshot:
        """Describe one menu item.

        Args:
            action: Its action.

        Returns:
            The item snapshot.
        """
        return ButtonSnapshot(
            text=self._texts.action_label(action),
            tooltip="",
            enabled=not self._gate.is_busy(action),
            visible=True,
            action=action,
        )

    def _show(self) -> ValidationResult:
        """Bring the main window to the front.

        Returns:
            Success.
        """
        self._attached().show_in_front()
        return ValidationResult.success()

    def _quit(self) -> ValidationResult:
        """Close the main window like its close button (the quit question follows).

        Returns:
            Success.
        """
        self._attached().request_close()
        return ValidationResult.success()

    def _attached(self) -> MainWindowPort:
        """The main window.

        Returns:
            The window given to ``attach``.

        Raises:
            RuntimeError: If ``attach`` was not called (a wiring error).
        """
        if self._window is None:
            raise RuntimeError(_NOT_ATTACHED)
        return self._window
