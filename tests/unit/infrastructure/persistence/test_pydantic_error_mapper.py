import json

import pytest
from pydantic import ValidationError

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.infrastructure.persistence.pydantic_error_mapper import code_for_error_type, validation_from_error
from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema

SETTINGS: dict[str, object] = {
    "id": "019a",
    "created_at": "2026-11-06T16:40:00Z",
    "updated_at": "2026-11-06T16:44:03Z",
    "language": 2,
}
VALID: dict[str, object] = {
    "schema_version": 1,
    "saved_at": "2026-11-06T16:44:03Z",
    "app_version": "0.1.0",
    "settings": SETTINGS,
}


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        ("missing", ErrorCodeEnum.STORAGE_FIELD_MISSING),
        ("extra_forbidden", ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED),
        ("int_type", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE),
        ("model_type", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE),
        ("datetime_parsing", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE),
        ("greater_than_equal", ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE),
        ("value_error", ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE),
    ],
)
def test_code_for_error_type(error_type: str, code: ErrorCodeEnum) -> None:
    assert code_for_error_type(error_type) is code


def _errors_for(document: object) -> ValidationError:
    with pytest.raises(ValidationError) as caught:
        UserDataSchema.model_validate_json(json.dumps(document))
    return caught.value


def test_valid_document_passes_the_schema() -> None:
    assert UserDataSchema.model_validate_json(json.dumps(VALID)).settings.language == 2


@pytest.mark.parametrize(
    ("document", "code", "field"),
    [
        (
            {key: value for key, value in VALID.items() if key != "app_version"},
            ErrorCodeEnum.STORAGE_FIELD_MISSING,
            "app_version",
        ),
        (
            {**VALID, "settings": {**SETTINGS, "language": "x"}},
            ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE,
            "settings.language",
        ),
        ({**VALID, "colour": "red"}, ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED, "colour"),
        ({**VALID, "schema_version": "1"}, ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "schema_version"),
        ({**VALID, "schema_version": 0}, ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE, "schema_version"),
        ({**VALID, "settings": []}, ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "settings"),
    ],
)
def test_each_error_family_maps_to_its_code_and_dotted_field(
    document: dict[str, object], code: ErrorCodeEnum, field: str
) -> None:
    result = validation_from_error(_errors_for(document))

    assert result.error_codes == (code,)
    assert result.issues[0].field == field
    assert result.issues[0].severity is SeverityEnum.ERROR
