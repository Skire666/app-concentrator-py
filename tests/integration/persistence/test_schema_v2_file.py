"""Schema version 2 is frozen (ADR-046, after ADR-044): the reference file must read and write unchanged."""

from collections.abc import Iterator
from pathlib import Path
from typing import Final

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.infrastructure.persistence.migrations.migration_chain import MigrationChain
from concentrator.infrastructure.persistence.migrations.schema_migration import Document, SchemaMigration
from concentrator.infrastructure.persistence.toml_user_data_file import TomlUserDataFile
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.immediate_dispatcher import ImmediateDispatcher
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import USER_DATA_LIMITS

REFERENCE_FILE: Final = Path(__file__).resolve().parents[2] / "data" / "schema-v2.toml"
APP_VERSION: Final = "2.0.0"
CODEC: Final = UserDataCodec(APP_VERSION, USER_DATA_LIMITS)
LEGACY_TASKS: Final = "todo_items"
TASKS: Final = "tasks"


def _reference_text() -> str:
    return REFERENCE_FILE.read_bytes().decode("utf-8")


def _rename_legacy_tasks(document: Document) -> Document:
    renamed = {key: value for key, value in document.items() if key != LEGACY_TASKS}
    if LEGACY_TASKS in document:
        renamed[TASKS] = document[LEGACY_TASKS]
    return renamed


def _v3_codec() -> UserDataCodec:
    """A codec of a pretend version 3 in which ``[[todo_items]]`` of version 2 became ``[[tasks]]``."""
    chain = MigrationChain(3, (SchemaMigration(from_version=2, migrate=_rename_legacy_tasks),))
    return UserDataCodec(APP_VERSION, USER_DATA_LIMITS, chain)


def test_reference_file_holds_every_section() -> None:
    text = _reference_text()

    for header in ("[settings]", "[timer]", "[[timer_presets]]", "[hourly_chime]", "[[task_lists]]", "[[tasks]]"):
        assert f"\n{header}\n" in text
    assert "focus_queue" not in text
    assert "recurrence = {" in text


def test_reference_file_reads_without_any_issue() -> None:
    result = CODEC.decode(_reference_text())

    assert result.is_success
    assert result.validation.issues == ()


def test_reference_file_is_written_back_byte_for_byte() -> None:
    stored = CODEC.decode(_reference_text()).data
    assert stored is not None

    assert CODEC.encode(stored).encode("utf-8") == REFERENCE_FILE.read_bytes()


def test_test_migration_upgrades_a_version_2_file() -> None:
    legacy = _reference_text().replace(f"[[{TASKS}]]", f"[[{LEGACY_TASKS}]]")
    current = CODEC.decode(_reference_text()).data
    assert current is not None
    assert current.data.tasks is not None

    migrated = _v3_codec().decode(legacy)

    assert migrated.data is not None
    assert migrated.data.data.schema_version == 3
    assert migrated.data.data.tasks == current.data.tasks


def test_version_2_file_without_the_migration_is_reported_by_the_schema() -> None:
    legacy = _reference_text().replace(f"[[{TASKS}]]", f"[[{LEGACY_TASKS}]]")

    assert ErrorCodeEnum.STORAGE_FIELD_UNEXPECTED in CODEC.decode(legacy).validation.error_codes


def test_migrated_file_is_written_at_the_new_version() -> None:
    stored = _v3_codec().decode(_reference_text().replace(f"[[{TASKS}]]", f"[[{LEGACY_TASKS}]]")).data
    assert stored is not None

    text = _v3_codec().encode(stored)

    assert text.startswith("# Concentrator user data. Schema version 3.\n")
    assert "\nschema_version = 3\n" in text
    assert f"[[{LEGACY_TASKS}]]" not in text


def test_a_version_older_than_every_step_is_refused() -> None:
    step = SchemaMigration(from_version=3, migrate=_rename_legacy_tasks)
    codec = UserDataCodec(APP_VERSION, USER_DATA_LIMITS, MigrationChain(4, (step,)))

    result = codec.decode(_reference_text())

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE,)
    assert result.validation.issues[0].field == "schema_version"


def test_version_3_file_is_refused_by_version_2() -> None:
    text = _reference_text().replace("\nschema_version = 2\n", "\nschema_version = 3\n")

    result = CODEC.decode(text)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED,)


def test_version_1_file_is_refused_without_migration() -> None:
    text = _reference_text().replace("\nschema_version = 2\n", "\nschema_version = 1\n")

    result = CODEC.decode(text)

    assert result.data is None
    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FIELD_INVALID_VALUE,)
    assert result.validation.issues[0].field == "schema_version"


@pytest.fixture
def adapter(tmp_path: Path) -> Iterator[TomlUserDataFile]:
    writer = WriterThread(ImmediateDispatcher(), RecordingErrorReporter())
    yield TomlUserDataFile(
        codec=CODEC, writer=writer, clock=FakeClock(), storage=make_storage_section(), backup_dir=tmp_path / "backups"
    )
    writer.shutdown()


def test_version_3_file_is_never_written_or_renamed_on_load(adapter: TomlUserDataFile, tmp_path: Path) -> None:
    path = tmp_path / "concentrator.toml"
    content = _reference_text().replace("\nschema_version = 2\n", "\nschema_version = 3\n").encode("utf-8")
    path.write_bytes(content)

    loaded = adapter.load(path)
    probed = adapter.probe(path)

    assert loaded.validation.error_codes == (ErrorCodeEnum.STORAGE_SCHEMA_VERSION_UNSUPPORTED,)
    assert probed.data is not None
    assert path.read_bytes() == content
    assert [item.name for item in tmp_path.iterdir()] == [path.name]
