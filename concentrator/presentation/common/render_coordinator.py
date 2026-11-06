"""The single entry point for rendering (AGENTS.md section 8.2)."""

import logging
from collections.abc import Callable
from typing import Final, Protocol, override

from concentrator.application.ports.scheduler_port import ScheduledCallPort, SchedulerPort
from concentrator.presentation.common.render_section_enum import RenderSectionEnum

_logger = logging.getLogger(__name__)

_NOTHING_RENDERED: Final = object()
_ALREADY_REGISTERED: Final = "render section already registered"


class _Refreshable(Protocol):
    """A registered section, with the snapshot type erased."""

    def refresh(self) -> bool:
        """Build the snapshot and render it if it changed; return whether it rendered."""
        ...


class _SectionBinding[S](_Refreshable):
    """Builder, renderer and last rendered snapshot of one section."""

    def __init__(self, build: Callable[[], S], render: Callable[[S], None]) -> None:
        self._build = build
        self._render = render
        self._last: object = _NOTHING_RENDERED

    @override
    def refresh(self) -> bool:
        """Build the snapshot once; render it only if it differs from the last rendered one.

        Returns:
            Whether ``render`` was called.
        """
        snapshot = self._build()
        if snapshot == self._last:
            return False
        self._render(snapshot)
        self._last = snapshot
        return True


class RenderCoordinator:
    """Collects render requests and flushes them once on the next event-loop turn."""

    def __init__(self, scheduler: SchedulerPort) -> None:
        """Create a coordinator without sections.

        Args:
            scheduler: Schedules the flush.
        """
        self._scheduler = scheduler
        self._bindings: dict[RenderSectionEnum, _Refreshable] = {}
        self._pending: set[RenderSectionEnum] = set()
        self._scheduled: ScheduledCallPort | None = None

    def register[S](
        self, section: RenderSectionEnum, build_snapshot: Callable[[], S], render: Callable[[S], None]
    ) -> None:
        """Bind a section to its snapshot builder and panel renderer (once per panel).

        Args:
            section: Section identifier.
            build_snapshot: Builds the complete, immutable snapshot of the panel.
            render: Panel ``render(snapshot)`` method.

        Raises:
            ValueError: If the section is already registered (programming error).
        """
        if section in self._bindings:
            raise ValueError(_ALREADY_REGISTERED)
        self._bindings[section] = _SectionBinding(build_snapshot, render)

    def request(self, *sections: RenderSectionEnum) -> None:
        """Ask for sections to be rendered on the next event-loop turn.

        Args:
            *sections: Sections whose content may have changed.
        """
        self._pending.update(sections)
        if self._pending and self._scheduled is None:
            self._scheduled = self._scheduler.call_soon(self.flush)

    def request_all(self) -> None:
        """Ask for every registered section (language change, data file switch)."""
        self.request(*self._bindings)

    def flush(self) -> None:
        """Render the pending sections now, in section order.

        Called by the scheduler; bootstrap also calls it once for the first render before the window is
        shown. Requests made while rendering are flushed on the next turn.
        """
        if self._scheduled is not None:
            self._scheduled.cancel()
            self._scheduled = None
        pending, self._pending = sorted(self._pending), set()
        for section in pending:
            binding = self._bindings.get(section)
            if binding is None:
                _logger.debug("Render requested for unregistered section %s", section.name)
                continue
            binding.refresh()
