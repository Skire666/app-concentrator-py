"""Opens the links written in the text of a task (ADR-014)."""

import logging
from typing import Final

from concentrator.application.ports.link_opener_port import LinkOpenerPort
from concentrator.application.ports.task_reader_port import TaskReaderPort
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.todo.link_detector import LinkDetector

_logger = logging.getLogger(__name__)

LINK_FIELD: Final = "link"


class LinkCommands:
    """Hands a link of a task to Windows, as it is; the log names the kind of the link, never the link."""

    def __init__(self, *, tasks: TaskReaderPort, links: LinkDetector, opener: LinkOpenerPort) -> None:
        """Create the use case.

        Args:
            tasks: Tasks reader.
            links: Finds the links of a text.
            opener: Windows shell.
        """
        self._tasks = tasks
        self._links = links
        self._opener = opener

    def open_link(self, task_id: str, index: int) -> ValidationResult:
        """Open the link number ``index`` of a task (links are numbered in reading order).

        Args:
            task_id: Task.
            index: Number of the link, from 0.

        Returns:
            Success, ``ENTITY_NOT_FOUND`` (task or link gone since the render) or the ``LINK_OPEN_FAILED``
            warning of the opener.
        """
        task = self._tasks.read_item(task_id)
        if task.data is None:
            return task.validation
        links = self._links.find(task.data.text)
        if not 0 <= index < len(links):
            _logger.warning("Link %d of a task not found (%d links)", index, len(links))
            return ValidationResult.failure(ErrorCodeEnum.ENTITY_NOT_FOUND, field=LINK_FIELD)
        target = links[index].target
        result = self._opener.open(target)
        if not result.has_warnings:
            _logger.info("Link opened (%s)", target.kind.name)
        return result
