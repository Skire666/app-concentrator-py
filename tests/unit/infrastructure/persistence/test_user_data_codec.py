from datetime import UTC, datetime

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.severity_enum import SeverityEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from tests.fakes.user_data_factory import SAVED_AT, SPEC_EXAMPLE_TEXT, USER_DATA_LIMITS, make_stored

CODEC = UserDataCodec(app_version="0.1.0", limits=USER_DATA_LIMITS)


def _edited(old: str, new: str) -> str:
    assert old in SPEC_EXAMPLE_TEXT
    return SPEC_EXAMPLE_TEXT.replace(old, new, 1)


def test_encode_writes_exactly_the_spec_example() -> None:
    assert CODEC.encode(make_stored(LanguageEnum.FRENCH)) == SPEC_EXAMPLE_TEXT


def test_encode_converts_a_non_utc_saved_at_and_drops_nothing_else() -> None:
    text = CODEC.encode(make_stored(saved_at=datetime(2026, 11, 6, 16, 44, 3, tzinfo=UTC)))

    assert text.endswith("end_hour = 20\n")
    assert "\r" not in text
    assert text.startswith("# Concentrator user data. Schema version 1.\n")


def test_decode_reads_the_spec_example() -> None:
    result = CODEC.decode(SPEC_EXAMPLE_TEXT)

    assert result.data == make_stored(LanguageEnum.FRENCH)


@pytest.mark.parametrize("language", [LanguageEnum.ENGLISH, LanguageEnum.FRENCH])
def test_round_trip_domain_file_domain_is_identical(language: LanguageEnum) -> None:
    stored = make_stored(language)

    assert CODEC.decode(CODEC.encode(stored)).data == stored


def test_decode_accepts_hand_written_toml() -> None:
    text = _edited("app_version = '0.1.0'\n", '# my note\n"app_version" = "0.1.0"   # trailing note\n')

    assert CODEC.decode(text.replace("\n", "\r\n")).data == make_stored()


def test_decode_accepts_native_toml_dates_typed_by_hand() -> None:
    text = _edited("created_at = '2026-11-06T16:40:00Z'", "created_at = 2026-11-06T16:40:00Z")

    assert CODEC.decode(text).data == make_stored()


def test_native_date_with_an_offset_is_reported_by_the_rules() -> None:
    result = CODEC.decode(_edited("created_at = '2026-11-06T16:40:00Z'", "created_at = 2026-11-06T17:40:00+01:00"))

    assert result.validation.error_codes == (ErrorCodeEnum.DATETIME_NOT_UTC,)
    assert result.validation.issues[0].field == "settings.created_at"


def test_unknown_enum_integer_is_reported_by_the_rules() -> None:
    result = CODEC.decode(_edited("language = 2", "language = 99"))

    assert result.validation.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)
    assert result.validation.issues[0].field == "settings.language"


@pytest.mark.parametrize(
    ("old", "new", "code", "field"),
    [
        ("language = 2", "language = 'x'", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "settings.language"),
        ("language = 2\n", "", ErrorCodeEnum.STORAGE_FIELD_MISSING, "settings.language"),
        ("language = 2\n", "language = 2\ntheme = 1\n", ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED, "settings.theme"),
        ("language = 2", "language = 0", ErrorCodeEnum.ENUM_VALUE_UNSET, "settings.language"),
        (
            "created_at = '2026-11-06T16:40:00Z'",
            "created_at = '2026-11-06T17:40:00+01:00'",
            ErrorCodeEnum.DATETIME_NOT_UTC,
            "settings.created_at",
        ),
        (
            "saved_at = '2026-11-06T16:44:03Z'",
            "saved_at = '2026-11-06T16:44:03'",
            ErrorCodeEnum.DATETIME_NOT_UTC,
            "saved_at",
        ),
        (
            "created_at = '2026-11-06T16:40:00Z'",
            "created_at = 'yesterday'",
            ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE,
            "settings.created_at",
        ),
        ("schema_version = 1", "schema_version = 0", ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE, "schema_version"),
        ("schema_version = 1", "schema_version = true", ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE, "schema_version"),
    ],
)
def test_invalid_content_is_reported_per_field(old: str, new: str, code: ErrorCodeEnum, field: str) -> None:
    result = CODEC.decode(_edited(old, new))

    assert result.data is None
    assert result.validation.error_codes == (code,)
    assert result.validation.issues[0].field == field


def test_newer_schema_version_is_refused_before_validation() -> None:
    result = CODEC.decode(_edited("schema_version = 1\n", "schema_version = 2\ntasks = []\n"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED,)
    assert result.validation.severity is SeverityEnum.CRITICAL


@pytest.mark.parametrize("text", ["", "# only a comment\n", "settings = 1\n"])
def test_empty_or_odd_document_is_a_structure_error(text: str) -> None:
    result = CODEC.decode(text)

    assert result.data is None
    assert result.validation.is_failure
    assert result.validation.error_codes[0].category.name == "STORAGE"


@pytest.mark.parametrize("number", ["inf", "-inf", "nan"])
def test_infinity_and_nan_are_invalid_values(number: str) -> None:
    result = CODEC.decode(_edited("schema_version = 1", f"schema_version = {number}"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE,)


def test_syntax_error_is_reported() -> None:
    result = CODEC.decode(_edited("language = 2", "language = 2,"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SYNTAX_INVALID,)


def test_duplicate_key_is_a_syntax_error() -> None:
    result = CODEC.decode(_edited("language = 2\n", "language = 2\nlanguage = 1\n"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SYNTAX_INVALID,)


def test_structure_errors_are_logged_without_values(caplog: pytest.LogCaptureFixture) -> None:
    CODEC.decode(_edited("language = 2", "language = 'my secret'"))

    assert "settings.language" in caplog.text
    assert "secret" not in caplog.text


def test_saved_at_is_returned_with_the_data() -> None:
    stored = CODEC.decode(SPEC_EXAMPLE_TEXT).data

    assert stored is not None
    assert stored.saved_at == SAVED_AT


def test_file_without_the_phase_4_settings_takes_the_ini_defaults() -> None:
    text = _edited("log_level = 2\nnotify_when_inactive = true\n", "")

    result = CODEC.decode(text)

    assert result.data == make_stored()
    assert CODEC.encode(make_stored()) == SPEC_EXAMPLE_TEXT


def test_unknown_log_level_is_reported_on_its_field() -> None:
    result = CODEC.decode(_edited("log_level = 2", "log_level = 9"))

    assert result.validation.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)
    assert result.validation.issues[0].field == "settings.log_level"


def test_log_level_written_as_text_is_a_type_error() -> None:
    result = CODEC.decode(_edited("log_level = 2", "log_level = 'INFO'"))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FIELD_INVALID_TYPE,)
