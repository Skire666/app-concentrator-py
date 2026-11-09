"""Whole read and write pipelines between file text and ``StoredUserData`` (no I/O).

Read: TOML text -> ``tomllib.loads`` (native dates as text) -> schema version check -> ``json.dumps``
-> ``model_validate_json`` -> mapper -> domain rules. Write: mapper -> DTO -> ``model_dump(mode="json")``
-> ``TomlCodec.encode`` -> header comment (ADR-035).
"""

import json
import logging
from typing import Final, cast

from pydantic import ValidationError

from concentrator.application.storage.user_data import CURRENT_SCHEMA_VERSION, StoredUserData, UserDataLimits
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.common.validation_issue import ValidationIssue
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.infrastructure.persistence.mappers.user_data_mapper import UserDataMapper
from concentrator.infrastructure.persistence.pydantic_error_mapper import validation_from_error
from concentrator.infrastructure.persistence.schemas.timer_preset_schema import TimerPresetSchema
from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema
from concentrator.infrastructure.persistence.toml_codec import TomlCodec

_logger = logging.getLogger(__name__)

SCHEMA_VERSION_FIELD: Final = "schema_version"
PRESETS_FIELD: Final = "timer_presets"
HEADER: Final = (
    "# Concentrator user data. Schema version {version}.\n"
    "# Close Concentrator before editing this file by hand. Comments are not preserved.\n"
)
LINE_END: Final = "\n"


def _newer_version(document: dict[str, object]) -> int | None:
    """Return the schema version of a parsed document when it is newer than this application.

    Args:
        document: Parsed TOML document.

    Returns:
        The newer version, or ``None`` (current, older, absent or not an integer: left to pydantic).
    """
    version = document.get(SCHEMA_VERSION_FIELD)
    if isinstance(version, int) and not isinstance(version, bool) and version > CURRENT_SCHEMA_VERSION:
        return version
    return None


def _readable_preset(index: int, element: object) -> bool:
    """Tell whether one ``[[timer_presets]]`` element has the expected structure.

    Args:
        index: Its position in the file.
        element: Parsed element.

    Returns:
        Whether it is kept; a broken element is logged at WARNING (error types only, no value).
    """
    try:
        TimerPresetSchema.model_validate_json(json.dumps(element, allow_nan=False, ensure_ascii=False))
    except ValidationError as error:
        details = [(".".join(map(str, item["loc"])), item["type"]) for item in error.errors(include_url=False)]
        _logger.warning("Favorite %d of the data file ignored: %s", index, details)
        return False
    except ValueError:
        _logger.warning("Favorite %d of the data file ignored: number that JSON cannot represent", index)
        return False
    return True


def _without_broken_presets(document: dict[str, object]) -> dict[str, object]:
    """Leave out the favorites whose structure is broken, so they never make the whole file unusable.

    Owner decision at the phase 3 review. A ``timer_presets`` value that is not an array is left to the
    schema, as any other structure error.

    Args:
        document: Parsed TOML document.

    Returns:
        The document with the readable favorites only.
    """
    elements = document.get(PRESETS_FIELD)
    if not isinstance(elements, list):
        return document
    readable = [
        element for index, element in enumerate(cast("list[object]", elements)) if _readable_preset(index, element)
    ]
    return {**document, PRESETS_FIELD: readable}


class UserDataCodec:
    """Converts between the file text and the stored data."""

    def __init__(self, app_version: str, limits: UserDataLimits) -> None:
        """Create the codec.

        Args:
            app_version: Version written in ``app_version``.
            limits: Bounds from ``concentrator.ini`` applied by the domain rules on read.
        """
        self._app_version = app_version
        self._limits = limits

    def decode(self, text: str) -> DataResult[StoredUserData]:
        """Run the read pipeline.

        Args:
            text: Whole file content (already decoded from UTF-8).

        Returns:
            The stored data, or the syntax, schema version, structure or rule failures.
        """
        parsed = TomlCodec.decode(text)
        if parsed.data is None:
            return DataResult.fail(parsed.validation)
        newer = _newer_version(parsed.data)
        if newer is not None:
            _logger.warning("Data file schema version %d is newer than %d", newer, CURRENT_SCHEMA_VERSION)
            issue = ValidationIssue(
                code=ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED,
                severity=SeverityEnum.CRITICAL,
                field=SCHEMA_VERSION_FIELD,
            )
            return DataResult.fail(ValidationResult.of(issue))
        return self._validate(_without_broken_presets(parsed.data))

    def encode(self, stored: StoredUserData) -> str:
        """Run the write pipeline.

        Args:
            stored: Data to write and the instant of this save.

        Returns:
            The file text: header comment, TOML document, final LF.
        """
        schema = UserDataMapper.to_schema(stored.data, stored.saved_at, self._app_version)
        document = TomlCodec.encode(schema.model_dump(mode="json"))
        return HEADER.format(version=stored.data.schema_version) + document + LINE_END

    def _validate(self, value: object) -> DataResult[StoredUserData]:
        """Validate a parsed document with pydantic, then map it to the domain.

        Args:
            value: Parsed TOML document.

        Returns:
            The stored data, or the failures.
        """
        try:
            json_text = json.dumps(value, allow_nan=False, ensure_ascii=False)
        except ValueError:
            _logger.warning("Data file contains a number that JSON cannot represent (NaN or Infinity)")
            return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE))
        try:
            schema = UserDataSchema.model_validate_json(json_text)
        except ValidationError as error:
            details = [(".".join(map(str, item["loc"])), item["type"]) for item in error.errors(include_url=False)]
            _logger.warning("Data file structure is invalid: %s", details)
            return DataResult.fail(validation_from_error(error))
        return UserDataMapper.to_domain(schema, self._limits)
