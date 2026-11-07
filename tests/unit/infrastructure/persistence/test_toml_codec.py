import tomllib

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.toml_codec import TomlCodec


def test_decode_reads_tables_arrays_and_comments() -> None:
    text = "# header\nversion = 1 # note\n\n[settings]\nname = 'x'\n\n[[tasks]]\ntags = ['a', \"b\"]\n"

    result = TomlCodec.decode(text)

    assert result.data == {"version": 1, "settings": {"name": "x"}, "tasks": [{"tags": ["a", "b"]}]}


def test_decode_turns_native_dates_and_times_into_iso_text() -> None:
    text = "[[events]]\nat = 2026-11-06T16:44:03Z\nday = 2026-11-10\nhour = 08:30:00\nlocal = 2026-11-06T16:44:03\n"

    result = TomlCodec.decode(text)

    assert result.data == {
        "events": [
            {"at": "2026-11-06T16:44:03+00:00", "day": "2026-11-10", "hour": "08:30:00", "local": "2026-11-06T16:44:03"}
        ]
    }


@pytest.mark.parametrize(
    ("text", "line", "column"),
    [
        ("a = 1\nb = ,\n", "2", "5"),
        ("a = 1\na = 2\n", "2", "6"),
        ("[s]\nx = 1\n[s]\n", "3", "3"),
        ("a = { b = 1,\n c = 2 }\n", "1", "13"),
    ],
)
def test_decode_reports_syntax_errors_and_duplicates_with_their_position(text: str, line: str, column: str) -> None:
    result = TomlCodec.decode(text)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SYNTAX_INVALID,)
    assert dict(result.validation.issues[0].params) == {"line": line, "column": column}


def test_decode_failure_logs_position_but_not_content(caplog: pytest.LogCaptureFixture) -> None:
    TomlCodec.decode("secret = 'my private task' oops\n")

    assert "line 1" in caplog.text
    assert "private" not in caplog.text


@pytest.mark.parametrize(
    ("value", "written"),
    [
        ("plain", "'plain'"),
        ("", "''"),
        ('C:\\Users\\me "q" https://x.org/?a=b&c', "'C:\\Users\\me \"q\" https://x.org/?a=b&c'"),
        ("tab\there", "'tab\there'"),
        ("é à ç € 😀 \ufeff", "'é à ç € 😀 \ufeff'"),
        ("l'arbitrage", "'''l'arbitrage'''"),
        ("'", "'''''''"),
        ("''", "''''''''"),
        ("'start", "''''start'''"),
        ("end'", "'''end''''"),
        ("''both''", "'''''both'''''"),
        ("a'''b", "\"a'''b\""),
        ("new\nline", '"new\\nline"'),
        ("cr\rlf\r\n", '"cr\\rlf\\r\\n"'),
        ("nul\x00 del\x7f bell\x07", '"nul\\u0000 del\\u007F bell\\u0007"'),
        ('back\\slash "q"\x08\x0c\n', '"back\\\\slash \\"q\\"\\b\\f\\n"'),
    ],
)
def test_strings_use_the_lightest_quoting_and_round_trip(value: str, written: str) -> None:
    text = TomlCodec.encode({"v": value})

    assert text == f"v = {written}"
    assert tomllib.loads(text) == {"v": value}


def test_encode_writes_the_file_layout() -> None:
    document: dict[str, object] = {
        "settings": {"id": "s", "enabled": True, "ratio": 0.5, "unset": None},
        "schema_version": 1,
        "tasks": [
            {
                "text": ["one", "two"],
                "sound": {"kind": 2, "value": "D:/a b.mp3", "unset": None},
                "weekdays": [],
                "history": [{"at": "2026-11-06T16:44:03Z", "details": {}, "tags": ["x", "y"]}],
            },
            {"text": [], "history": []},
        ],
        "focus_queue": [],
        "odd key": "x",
        "unset": None,
    }

    text = TomlCodec.encode(document)

    assert text == (
        "schema_version = 1\n"
        "focus_queue = []\n"
        "'odd key' = 'x'\n"
        "\n"
        "[settings]\n"
        "id = 's'\n"
        "enabled = true\n"
        "ratio = 0.5\n"
        "\n"
        "[[tasks]]\n"
        "text = [\n"
        "  'one',\n"
        "  'two',\n"
        "]\n"
        "sound = { kind = 2, value = 'D:/a b.mp3' }\n"
        "weekdays = []\n"
        "history = [\n"
        "  { at = '2026-11-06T16:44:03Z', details = {}, tags = ['x', 'y'] },\n"
        "]\n"
        "\n"
        "[[tasks]]\n"
        "text = []\n"
        "history = []"
    )
    assert tomllib.loads(text) == {
        "schema_version": 1,
        "focus_queue": [],
        "odd key": "x",
        "settings": {"id": "s", "enabled": True, "ratio": 0.5},
        "tasks": [
            {
                "text": ["one", "two"],
                "sound": {"kind": 2, "value": "D:/a b.mp3"},
                "weekdays": [],
                "history": [{"at": "2026-11-06T16:44:03Z", "details": {}, "tags": ["x", "y"]}],
            },
            {"text": [], "history": []},
        ],
    }


def test_encode_without_root_scalars_starts_with_the_first_section() -> None:
    assert TomlCodec.encode({"empty": {}, "nested": [[1, 2], ["a"]]}) == "nested = [\n  [1, 2],\n  ['a'],\n]\n\n[empty]"


@pytest.mark.parametrize("value", [object(), [None], {"a": [object()]}])
def test_encode_refuses_values_toml_cannot_hold(value: object) -> None:
    with pytest.raises(TypeError, match="as TOML"):
        TomlCodec.encode({"v": value})


@pytest.mark.parametrize(
    ("key", "written"),
    [
        ("plain_key-1", "plain_key-1"),
        ("odd key", "'odd key'"),
        ("l'été", '"l\'été"'),
        ("a'''b", "\"a'''b\""),
        ('quote "x" \\', "'quote \"x\" \\'"),
        ("line\nbreak", '"line\\nbreak"'),
        ("", "''"),
    ],
)
def test_keys_are_bare_or_single_line_quoted_and_round_trip(key: str, written: str) -> None:
    text = TomlCodec.encode({"table": {key: 1}})

    assert text == f"[table]\n{written} = 1"
    assert tomllib.loads(text) == {"table": {key: 1}}
