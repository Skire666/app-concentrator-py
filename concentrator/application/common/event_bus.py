"""Synchronous publish/subscribe between features."""

import logging
from collections import defaultdict
from collections.abc import Callable
from typing import cast

from concentrator.application.ports.error_reporter_port import ErrorReporterPort

_logger = logging.getLogger(__name__)

type _Handler = Callable[[object], None]


class EventBus:
    """Delivers each published event to the handlers subscribed to its exact type, in order.

    A failing handler does not stop the others: its exception is logged with the traceback and
    forwarded to the error reporter shared with the global exception hooks (ADR-021).
    """

    def __init__(self, error_reporter: ErrorReporterPort) -> None:
        """Create an empty bus.

        Args:
            error_reporter: Receives the exceptions raised by handlers.
        """
        self._error_reporter = error_reporter
        self._handlers: defaultdict[type, list[_Handler]] = defaultdict(list)

    def subscribe[E](self, event_type: type[E], handler: Callable[[E], None]) -> None:
        """Register a handler for one event type.

        Args:
            event_type: Exact class of the events to receive.
            handler: Called synchronously with each published event of that class.
        """
        self._handlers[event_type].append(cast("_Handler", handler))

    def publish(self, event: object) -> None:
        """Deliver an event to its handlers.

        Handlers subscribed while the event is being delivered only receive later events.

        Args:
            event: Immutable event instance.
        """
        for handler in tuple(self._handlers.get(type(event), ())):
            self._deliver(handler, event)

    def _deliver(self, handler: _Handler, event: object) -> None:
        """Call one handler, isolating its failure.

        Args:
            handler: Handler to call.
            event: Event to deliver.
        """
        try:
            handler(event)
        except Exception as error:  # AGENTS.md rule 4: EventBus dispatch is one of the two allowed places.
            _logger.exception("Event handler %r failed on %s", handler, type(event).__name__)
            self._error_reporter.report(error)
