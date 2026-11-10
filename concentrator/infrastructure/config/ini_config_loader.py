"""``concentrator.ini`` -> ``configparser`` -> ``AppConfigSchema`` -> ``AppConfig``."""

import configparser
import logging
from pathlib import Path
from typing import Final

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from concentrator.application.common.app_config import (
    AppConfig,
    AppSection,
    ChimeSection,
    I18nSection,
    JournalSection,
    LoggingSection,
    PathsSection,
    SettingsSection,
    StorageSection,
    TimerSection,
    TodoSection,
    UiSection,
)
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.domain.todo.priority_enum import PriorityEnum
from concentrator.domain.todo.task_sort_key_enum import TaskSortKeyEnum
from concentrator.infrastructure.config.app_config_schema import (
    AppConfigSchema,
    JournalSectionSchema,
    LoggingSectionSchema,
    PathsSectionSchema,
    SettingsSectionSchema,
    TimerSectionSchema,
    TodoSectionSchema,
    number_list,
)
from concentrator.infrastructure.system.app_paths import AppPaths

_logger = logging.getLogger(__name__)

_ERROR_TYPE_CODES: Final = {
    "missing": ErrorCodeEnum.CONFIG_KEY_MISSING,
    "extra_forbidden": ErrorCodeEnum.CONFIG_KEY_UNEXPECTED,
}
_PATH_KEYS: Final = ("default_data_file", "ui_state_file", "log_dir", "backup_dir")
_PRESETS_KEY: Final = "default_presets_minutes"
_COLUMN_WIDTHS_KEY: Final = "default_column_widths_px"
_PRIORITY_KEY: Final = "default_list_priority"
_SORT_KEY: Final = "default_sort"


def _issue_from_error(error: ErrorDetails) -> ValidationIssue:
    """Convert one pydantic error into a coded issue.

    Args:
        error: One entry of ``ValidationError.errors()``.

    Returns:
        The issue; ``field`` is the dotted ``section.key`` path.
    """
    code = _ERROR_TYPE_CODES.get(error["type"], ErrorCodeEnum.CONFIG_VALUE_INVALID)
    field_path = ".".join(str(part) for part in error["loc"])
    return ValidationIssue(code=code, severity=SeverityEnum.ERROR, field=field_path)


def _timer_section(section: TimerSectionSchema) -> TimerSection:
    """Map ``[timer]``, turning the favorites list into integers.

    Args:
        section: Validated DTO.

    Returns:
        The section.
    """
    return TimerSection(**section.model_dump(exclude={_PRESETS_KEY}), default_presets_minutes=section.preset_minutes())


def _logging_section(section: LoggingSectionSchema) -> LoggingSection:
    """Map ``[logging]``, turning the level name into its number.

    Args:
        section: Validated DTO.

    Returns:
        The section.
    """
    return LoggingSection(
        level=logging.getLevelNamesMapping()[section.level],
        file_name=section.file_name,
        file_max_bytes=section.file_max_bytes,
        file_backup_count=section.file_backup_count,
        journal_buffer_size=section.journal_buffer_size,
    )


def _journal_section(section: JournalSectionSchema) -> JournalSection:
    """Map ``[journal]``, turning the column widths into integers.

    Args:
        section: Validated DTO.

    Returns:
        The section.
    """
    return JournalSection(
        **section.model_dump(exclude={_COLUMN_WIDTHS_KEY}), default_column_widths_px=section.column_widths()
    )


def _todo_section(section: TodoSectionSchema) -> TodoSection:
    """Map ``[todo]``, turning the names into members and the column widths into integers.

    Args:
        section: Validated DTO.

    Returns:
        The section.
    """
    names = {_PRIORITY_KEY, _SORT_KEY, _COLUMN_WIDTHS_KEY}
    return TodoSection(
        **section.model_dump(exclude=names),
        default_list_priority=PriorityEnum[section.default_list_priority],
        default_sort=TaskSortKeyEnum[section.default_sort],
        default_column_widths_px=number_list(section.default_column_widths_px),
    )


def _settings_section(section: SettingsSectionSchema) -> SettingsSection:
    """Map ``[settings]``, turning the level name into its member.

    Args:
        section: Validated DTO.

    Returns:
        The section.
    """
    return SettingsSection(
        default_log_level=LogLevelEnum[section.default_log_level],
        default_notify_when_inactive=section.default_notify_when_inactive,
    )


class IniConfigLoader:
    """Reads and validates ``concentrator.ini``. A missing or invalid key is a failure, never a default."""

    def __init__(self, paths: AppPaths) -> None:
        """Create a loader.

        Args:
            paths: Used to resolve the path tokens.
        """
        self._paths = paths

    def load(self, config_file: Path) -> DataResult[AppConfig]:
        """Load the configuration.

        Args:
            config_file: Path of ``concentrator.ini``.

        Returns:
            The configuration, or ``CONFIG_FILE_NOT_FOUND``, ``CONFIG_SYNTAX_INVALID``,
            ``CONFIG_KEY_MISSING``, ``CONFIG_KEY_UNEXPECTED`` or ``CONFIG_VALUE_INVALID`` issues.
        """
        sections = self._read_sections(config_file)
        if sections.data is None:
            return DataResult.fail(sections.validation)
        try:
            schema = AppConfigSchema.model_validate_strings(sections.data)
        except ValidationError as error:
            _logger.warning("Invalid configuration %s: %s", config_file, error.errors(include_url=False))
            return DataResult.fail(ValidationResult.of(*(_issue_from_error(item) for item in error.errors())))
        return self._to_app_config(schema)

    @staticmethod
    def _read_sections(config_file: Path) -> DataResult[dict[str, dict[str, str]]]:
        """Parse the ini text into plain dictionaries.

        Args:
            config_file: Path of the ini file.

        Returns:
            Section name to key-value pairs, or a file/syntax failure.
        """
        try:
            text = config_file.read_text(encoding="utf-8")
        except FileNotFoundError:
            _logger.warning("Configuration file not found: %s", config_file)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CONFIG_FILE_NOT_FOUND, path=config_file))
        except (OSError, UnicodeDecodeError) as error:
            _logger.warning("Cannot read configuration file %s: %s", config_file, error)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CONFIG_SYNTAX_INVALID, path=config_file))
        parser = configparser.ConfigParser(interpolation=None)
        try:
            parser.read_string(text, source=str(config_file))
        except configparser.Error as error:
            _logger.warning("Configuration syntax error in %s: %s", config_file, error)
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.CONFIG_SYNTAX_INVALID, path=config_file))
        return DataResult.ok({name: dict(parser.items(name)) for name in parser.sections()})

    def _to_app_config(self, schema: AppConfigSchema) -> DataResult[AppConfig]:
        """Map the validated DTO to the application dataclasses, resolving the path tokens.

        Args:
            schema: Validated DTO.

        Returns:
            The configuration, or ``CONFIG_VALUE_INVALID`` for an unresolvable path.
        """
        paths = self._resolve_paths(schema.paths)
        if paths.data is None:
            return DataResult.fail(paths.validation)
        return DataResult.ok(
            AppConfig(
                app=AppSection(**schema.app.model_dump()),
                paths=paths.data,
                ui=UiSection(**schema.ui.model_dump()),
                storage=StorageSection(**schema.storage.model_dump()),
                timer=_timer_section(schema.timer),
                chime=ChimeSection(**schema.chime.model_dump()),
                todo=_todo_section(schema.todo),
                logging=_logging_section(schema.logging),
                journal=_journal_section(schema.journal),
                settings=_settings_section(schema.settings),
                i18n=I18nSection(
                    default_language=LanguageEnum.from_iso_code(schema.i18n.default_language),
                    fallback_language=LanguageEnum.from_iso_code(schema.i18n.fallback_language),
                ),
            )
        )

    def _resolve_paths(self, section: PathsSectionSchema) -> DataResult[PathsSection]:
        """Resolve every path template of ``[paths]``.

        Args:
            section: Validated ``[paths]`` DTO.

        Returns:
            Resolved paths, or every resolution failure.
        """
        templates = section.model_dump()
        results = {key: self._paths.resolve(templates[key], f"paths.{key}") for key in _PATH_KEYS}
        failures = [result.validation for result in results.values() if result.data is None]
        if failures:
            return DataResult.fail(failures[0].merge(*failures[1:]))
        return DataResult.ok(PathsSection(**{key: result.value_or(Path()) for key, result in results.items()}))
