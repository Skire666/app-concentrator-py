"""Events published by the focus queue use cases."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class FocusQueueChangedEvent:
    """Tasks were queued, removed from the queue, or the queue was reordered.

    Attributes:
        task_ids: Tasks concerned (their star in the task table and their history changed).
    """

    task_ids: tuple[str, ...]
