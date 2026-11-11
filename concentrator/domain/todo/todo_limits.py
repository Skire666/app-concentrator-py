"""Limits of the TODO feature, built from ``concentrator.ini`` by the application layer."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class TodoLimits:
    """Bounds used by ``TaskRules`` and ``TaskListRules`` and by the history of a task.

    Attributes:
        max_task_text_length: Longest task text, in characters (lines joined with one line break).
        max_list_name_length: Longest list name, in characters.
        max_list_description_length: Longest list description, in characters.
        max_history_events: Most events kept in the history of a task (the first one included).
        max_recurrence_interval: Largest interval of a recurrence.
        max_recurrence_count: Largest number of occurrences of a recurrence that ends after a count.
    """

    max_task_text_length: int
    max_list_name_length: int
    max_list_description_length: int
    max_history_events: int
    max_recurrence_interval: int
    max_recurrence_count: int
