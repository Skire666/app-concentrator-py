"""Everything stored in the user data file, as one immutable snapshot."""

from dataclasses import dataclass, replace
from datetime import datetime
from typing import Final, Self

from concentrator.application.settings.settings_defaults import SettingsDefaults
from concentrator.domain.settings.user_settings import UserSettings
from concentrator.domain.timer.hourly_chime import HourlyChime
from concentrator.domain.timer.timer_config import TimerConfig
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection
from concentrator.domain.todo.task_lists_collection import TaskListsCollection
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.domain.todo.todo_limits import TodoLimits

CURRENT_SCHEMA_VERSION: Final = 1


@dataclass(frozen=True, slots=True, kw_only=True)
class UserData:
    """The whole content of the user data file. Later phases add sections with defaults.

    A section missing from a file read from disk is ``None`` until ``UserDataDefaults`` fills it
    in with the ``concentrator.ini`` defaults, right after the file is opened.

    Attributes:
        schema_version: Version of the file layout (``CURRENT_SCHEMA_VERSION`` for new files).
        settings: Personal settings.
        timer: Timer configuration (``[timer]``, phase 2).
        timer_presets: Favorites (``[[timer_presets]]``, phase 3); ``None`` when the file has no
            ``timer_presets`` key, an empty collection when the user deleted every favorite.
        hourly_chime: Hourly chime (``[hourly_chime]``, phase 3).
        task_lists: TODO lists (``[[task_lists]]``, phase 5); ``None`` or empty until the first list
            (Inbox) is created.
        tasks: Tasks of every list (``[[tasks]]``, phase 5).
    """

    schema_version: int
    settings: UserSettings
    timer: TimerConfig | None = None
    timer_presets: TimerPresetsCollection | None = None
    hourly_chime: HourlyChime | None = None
    task_lists: TaskListsCollection | None = None
    tasks: TasksCollection | None = None

    @classmethod
    def initial(
        cls,
        settings: UserSettings,
        timer: TimerConfig,
        timer_presets: TimerPresetsCollection,
        hourly_chime: HourlyChime,
        task_lists: TaskListsCollection,
    ) -> Self:
        """Content of a new data file.

        Args:
            settings: Settings of the new file.
            timer: Timer configuration of the new file.
            timer_presets: Favorites of the new file.
            hourly_chime: Hourly chime of the new file.
            task_lists: Lists of the new file (the Inbox).

        Returns:
            The data, at the current schema version.
        """
        return cls(
            schema_version=CURRENT_SCHEMA_VERSION,
            settings=settings,
            timer=timer,
            timer_presets=timer_presets,
            hourly_chime=hourly_chime,
            task_lists=task_lists,
            tasks=TasksCollection(),
        )

    def with_settings(self, settings: UserSettings) -> Self:
        """Return a copy with other settings.

        Args:
            settings: New settings.

        Returns:
            The changed data.
        """
        return replace(self, settings=settings)

    def with_timer(self, timer: TimerConfig) -> Self:
        """Return a copy with another timer configuration.

        Args:
            timer: New configuration.

        Returns:
            The changed data.
        """
        return replace(self, timer=timer)

    def with_timer_presets(self, timer_presets: TimerPresetsCollection) -> Self:
        """Return a copy with other favorites.

        Args:
            timer_presets: New favorites.

        Returns:
            The changed data.
        """
        return replace(self, timer_presets=timer_presets)

    def with_hourly_chime(self, hourly_chime: HourlyChime) -> Self:
        """Return a copy with another hourly chime.

        Args:
            hourly_chime: New chime.

        Returns:
            The changed data.
        """
        return replace(self, hourly_chime=hourly_chime)

    def with_task_lists(self, task_lists: TaskListsCollection) -> Self:
        """Return a copy with other lists.

        Args:
            task_lists: New lists.

        Returns:
            The changed data.
        """
        return replace(self, task_lists=task_lists)

    def with_tasks(self, tasks: TasksCollection) -> Self:
        """Return a copy with other tasks.

        Args:
            tasks: New tasks.

        Returns:
            The changed data.
        """
        return replace(self, tasks=tasks)


@dataclass(frozen=True, slots=True, kw_only=True)
class UserDataLimits:
    """Values from ``concentrator.ini`` that the read pipeline needs.

    Attributes:
        timer: Bounds of the timer configuration and of the favorites, applied by the domain rules.
        settings: Values of the ``[settings]`` keys that a file written before phase 4 does not have.
        todo: Bounds of the lists and tasks, applied by the domain rules.
    """

    timer: TimerLimits
    settings: SettingsDefaults
    todo: TodoLimits


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredUserData:
    """User data together with the instant it was saved (``saved_at`` of the file).

    Attributes:
        data: The content.
        saved_at: When the file was written, timezone-aware UTC.
    """

    data: UserData
    saved_at: datetime
