"""Limits of the focus queue, built from ``concentrator.ini`` by the application layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusLimits:
    """Bounds used by ``FocusRules``.

    Attributes:
        max_items: Most items in the queue (``focus.max_items``).
    """

    max_items: int
