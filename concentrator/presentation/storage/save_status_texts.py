"""Status bar text and tooltip of the save state."""

from dataclasses import dataclass
from typing import Final

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.application.storage.save_state_enum import SaveStateEnum
from concentrator.application.storage.storage_events import SaveStatusChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.storage.storage_messages import StorageMessages

LINE_BREAK: Final = "\n"


@dataclass(frozen=True, slots=True)
class SaveStatusText:
    """What the status bar shows about saving.

    Attributes:
        text: One-line state.
        tooltip: Data file path and the issues of the last save.
    """

    text: str
    tooltip: str


class SaveStatusTexts:
    """``Saved at 17:44:03``, ``Saving...``, ``Unsaved changes``, ``Save failed: ...``, ``No data file``."""

    def __init__(self, translator: TranslatorPort, formatter: DateTimeFormatter) -> None:
        """Create the texts.

        Args:
            translator: Current-language translator.
            formatter: Local time of the last save.
        """
        self._translator = translator
        self._formatter = formatter
        self._messages = StorageMessages(translator)

    def describe(self, status: SaveStatusChangedEvent) -> SaveStatusText:
        """Describe a save status.

        Args:
            status: Last status of the save coordinator.

        Returns:
            The text and tooltip.
        """
        tooltip_lines = (
            []
            if status.path is None
            else [self._translator.tr("status.save.tooltip.path", path=status.path.as_posix())]
        )
        tooltip_lines.extend(self._messages.line(issue) for issue in status.validation.issues)
        return SaveStatusText(text=self._text(status), tooltip=LINE_BREAK.join(tooltip_lines))

    def _text(self, status: SaveStatusChangedEvent) -> str:
        """One-line state.

        Args:
            status: Save status.

        Returns:
            The text.
        """
        tr = self._translator.tr
        match status.state:
            case SaveStateEnum.SAVED if status.saved_at is not None:
                return tr("status.save.saved_at", time=self._formatter.time_with_seconds(status.saved_at))
            case SaveStateEnum.SAVED:
                return tr("status.save.saved")
            case SaveStateEnum.PENDING:
                return tr("status.save.pending")
            case SaveStateEnum.SAVING:
                return tr("status.save.saving")
            case SaveStateEnum.FAILED:
                return self._failure_text(status)
            case _:
                return tr("status.save.no_file")

    def _failure_text(self, status: SaveStatusChangedEvent) -> str:
        """``Save failed: <reason> Retrying.``, or the stopped variant after an external change.

        Args:
            status: Failed status.

        Returns:
            The text.
        """
        reason = self._messages.first(status.validation)
        if ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY in status.validation.error_codes:
            return self._translator.tr("status.save.stopped", reason=reason)
        return self._translator.tr("status.save.failed", reason=reason)
