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
    I18nSection,
    LoggingSection,
    PathsSection,
    StorageSection,
    TimerSection,
    UiSection,
)
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.config.app_config_schema import AppConfigSchema, PathsSectionSchema
from concentrator.infrastructure.system.app_paths import AppPaths

_logger = logging.getLogger(__name__)

_ERROR_TYPE_CODES: Final = {
    "missing": ErrorCodeEnum.CONFIG_KEY_MISSING,
    "extra_forbidden": ErrorCodeEnum.CONFIG_KEY_UNEXPECTED,
}
_PATH_KEYS: Final = ("default_data_file", "ui_state_file", "log_dir", "backup_dir")


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
                timer=TimerSection(**schema.timer.model_dump()),
                logging=LoggingSection(
                    level=logging.getLevelNamesMapping()[schema.logging.level],
                    file_name=schema.logging.file_name,
                    file_max_bytes=schema.logging.file_max_bytes,
                    file_backup_count=schema.logging.file_backup_count,
                    journal_buffer_size=schema.logging.journal_buffer_size,
                ),
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
