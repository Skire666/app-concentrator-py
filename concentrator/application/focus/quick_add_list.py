"""Finds the list that receives the tasks typed in the quick-add field of the focus queue."""

import logging

from concentrator.application.ports.task_list_reader_port import TaskListReaderPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.user_data_defaults import INBOX_NAME_KEY
from concentrator.application.todo.task_list_commands import ListValues, TaskListCommands
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.multiline_text import MultilineText
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_list import TaskList
from concentrator.domain.todo.task_lists_collection import TaskListsCollection

_logger = logging.getLogger(__name__)


class QuickAddList:
    """The quick-add list: the chosen one, else the Inbox, created when missing (phase 7 spec)."""

    def __init__(
        self,
        *,
        lists: TaskListReaderPort,
        list_commands: TaskListCommands,
        translator: TranslatorPort,
        priority: PriorityEnum,
    ) -> None:
        """Create the resolver.

        Args:
            lists: Lists reader.
            list_commands: Creates the Inbox when no list has its name.
            translator: Names the Inbox in the current language.
            priority: Priority of a created Inbox (``todo.default_list_priority``).
        """
        self._lists = lists
        self._list_commands = list_commands
        self._translator = translator
        self._priority = priority

    def find(self, preferred_list_id: str) -> TaskList | None:
        """Find the list without creating one.

        Args:
            preferred_list_id: List chosen by the user (``""`` for none).

        Returns:
            The chosen list when it exists, else the first list named like the translated "Inbox", else
            ``None``.
        """
        lists = self._lists.all_items().value_or(TaskListsCollection())
        chosen = lists.get(preferred_list_id).data if preferred_list_id else None
        return chosen or lists.ordered().with_name(self._translator.tr(INBOX_NAME_KEY))

    def resolve(self, preferred_list_id: str) -> DataResult[TaskList]:
        """Find the list, creating an Inbox when needed.

        Args:
            preferred_list_id: List chosen by the user (``""`` for none).

        Returns:
            The list, or the failure of the Inbox creation.
        """
        found = self.find(preferred_list_id)
        if found is not None:
            return DataResult.ok(found)
        _logger.info("Inbox list created for the focus quick add")
        values = ListValues(
            name=self._translator.tr(INBOX_NAME_KEY), description=MultilineText(), priority=self._priority
        )
        return self._list_commands.create(values)
