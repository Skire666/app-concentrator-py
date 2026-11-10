"""Page switching and window title of the window shell (the status bar has its own presenter)."""

import logging
from collections.abc import Callable
from itertools import starmap
from types import MappingProxyType
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.timer.timer_events import TimerChangedEvent
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
BADGE_MAX: Final = 99

type PageListener = Callable[[ShellPageEnum], None]
type LeaveGuard = Callable[[], bool]


def _never() -> bool:
    """Default ringing state: no timer.

    Returns:
        ``False``.
    """
    return False


def _no_badge() -> int:
    """Default journal badge: no new error.

    Returns:
        0.
    """
    return 0


class ShellPresenter:
    """Builds the ``SHELL`` snapshot and handles the module bar actions.

    While the timer rings and another page is shown, the Focus button is highlighted. The Journal button
    shows the number of errors logged while the journal was hidden. A page may refuse to be left (the
    settings page with unsaved changes asks first); page listeners learn which page is shown.
    """

    def __init__(
        self,
        translator: TranslatorPort,
        gate: ActionGate,
        renderer: RenderCoordinator,
        timer_ringing: Callable[[], bool] = _never,
        journal_badge: Callable[[], int] = _no_badge,
    ) -> None:
        """Create the presenter; the Focus page is shown first.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            timer_ringing: Tells whether the timer is ringing.
            journal_badge: Number of errors logged while the journal was hidden.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._timer_ringing = timer_ringing
        self._journal_badge = journal_badge
        self._active_page = ShellPageEnum.FOCUS
        self._listeners: list[PageListener] = []
        self._leave_guards: dict[ShellPageEnum, LeaveGuard] = {}

    @property
    def active_page(self) -> ShellPageEnum:
        """Page currently shown."""
        return self._active_page

    def add_page_listener(self, listener: PageListener) -> None:
        """Call a function each time another page is shown.

        Args:
            listener: Receives the page now shown.
        """
        self._listeners.append(listener)

    def set_leave_guard(self, page: ShellPageEnum, guard: LeaveGuard) -> None:
        """Ask a page before it is left.

        Args:
            page: Guarded page.
            guard: Returns whether the page may be left (it may ask the user).
        """
        self._leave_guards[page] = guard

    def show_page(self, page: ShellPageEnum) -> ValidationResult:
        """Show a page, if the page shown now may be left.

        Args:
            page: Page to show.

        Returns:
            Success, or skipped when the current page stays.
        """
        if page is self._active_page:
            return ValidationResult.success()
        guard = self._leave_guards.get(self._active_page)
        if guard is not None and not guard():
            _logger.info("Page %s kept: leaving it was cancelled", self._active_page.name)
            return ValidationResult.skipped()
        self._active_page = page
        self._renderer.request(RenderSectionEnum.SHELL)
        for listener in self._listeners:
            listener(page)
        return ValidationResult.success()

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
            journal_placeholder=tr("placeholder.journal"),
            settings_placeholder=tr("placeholder.settings"),
        )

    def on_timer_changed(self, event: TimerChangedEvent) -> None:
        """Re-render the module bar when the timer starts or stops ringing.

        Args:
            event: Published by the timer engine; only transitions matter here.
        """
        if event.transitions:
            self._renderer.request(RenderSectionEnum.SHELL)

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
        interactive = self._active_page in self._leave_guards
        result = self._gate.run(action, lambda: self.show_page(page), interactive=interactive)
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
        badge = self._journal_badge() if page is ShellPageEnum.JOURNAL and page is not self._active_page else 0
        tooltip = self._texts.action_tooltip(action)
        if badge:
            badge_tooltip = self._translator.tr_plural("shell.journal.badge.tooltip", badge)
            tooltip = f"{tooltip}\n{badge_tooltip}" if tooltip else badge_tooltip
        return ModuleButtonSnapshot(
            text=self._texts.action_label(action),
            tooltip=tooltip,
            checked=page is self._active_page,
            highlighted=page is ShellPageEnum.FOCUS and page is not self._active_page and self._timer_ringing(),
            enabled=not self._gate.is_busy(action),
            action=action,
            badge=self._badge_text(badge),
        )

    def _badge_text(self, count: int) -> str:
        """Write a badge count.

        Args:
            count: Number to show.

        Returns:
            ``""`` for 0, the number up to ``BADGE_MAX``, then ``99+``.
        """
        if count <= 0:
            return ""
        if count > BADGE_MAX:
            return self._translator.tr("shell.badge.overflow", max=BADGE_MAX)
        return str(count)
