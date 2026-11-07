import codecs
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

from concentrator.application.storage.file_state_enum import FileStateEnum
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_outcome import SaveOutcome
from concentrator.application.storage.user_data import UserData
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.infrastructure.persistence.toml_user_data_file import TomlUserDataFile
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.writer_thread import WriterThread
from tests.fakes.app_config_factory import make_storage_section
from tests.fakes.fake_clock import FakeClock
from tests.fakes.immediate_dispatcher import ImmediateDispatcher
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import SPEC_EXAMPLE_TEXT, make_stored, make_user_data

TIMEOUT_MS = 5000
CODEC = UserDataCodec(app_version="0.1.0")


@pytest.fixture
def writer() -> Iterator[WriterThread]:
    thread = WriterThread(ImmediateDispatcher(), RecordingErrorReporter())
    yield thread
    thread.shutdown()


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def adapter(tmp_path: Path, writer: WriterThread, clock: FakeClock) -> TomlUserDataFile:
    return TomlUserDataFile(
        codec=CODEC, writer=writer, clock=clock, storage=make_storage_section(), backup_dir=tmp_path / "backups"
    )


@pytest.fixture
def path(tmp_path: Path) -> Path:
    return tmp_path / "data" / "concentrator.toml"


def _side(path: Path, suffix: str) -> Path:
    return path.with_name(path.name + suffix)


def _save(adapter: TomlUserDataFile, path: Path, data: UserData, *, overwrite: bool = False) -> SaveOutcome:
    outcomes: list[SaveOutcome] = []
    adapter.save_async(path, data, 7, outcomes.append, overwrite_external=overwrite)
    assert adapter.flush(TIMEOUT_MS).is_success
    assert len(outcomes) == 1
    return outcomes[0]


def test_create_writes_the_file_with_the_clock_time(adapter: TomlUserDataFile, path: Path, clock: FakeClock) -> None:
    result = adapter.create(path, make_user_data())

    assert result.data is not None
    assert result.data.saved_at == clock.now_utc()
    assert adapter.exists(path)
    assert path.read_text(encoding="utf-8") == CODEC.encode(result.data)


def test_create_refuses_an_existing_file(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data())

    result = adapter.create(path, make_user_data(LanguageEnum.ENGLISH))

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_ALREADY_EXISTS,)


def test_create_where_no_folder_can_exist(adapter: TomlUserDataFile, tmp_path: Path) -> None:
    (tmp_path / "blocker").write_text("file", encoding="utf-8")

    result = adapter.create(tmp_path / "blocker" / "concentrator.toml", make_user_data())

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_DIRECTORY_NOT_WRITABLE,)


def test_load_reads_the_spec_example_and_accepts_a_bom(adapter: TomlUserDataFile, path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_bytes(codecs.BOM_UTF8 + SPEC_EXAMPLE_TEXT.encode("utf-8"))

    result = adapter.load(path)

    assert result.data is not None
    assert result.data.data.settings.language is LanguageEnum.FRENCH


@pytest.mark.parametrize(
    ("content", "code"),
    [(None, ErrorCodeEnum.STORAGE_FILE_NOT_FOUND), (b"\xff\xfe{", ErrorCodeEnum.STORAGE_ENCODING_INVALID)],
)
def test_load_failures(adapter: TomlUserDataFile, path: Path, content: bytes | None, code: ErrorCodeEnum) -> None:
    if content is not None:
        path.parent.mkdir(parents=True)
        path.write_bytes(content)

    assert adapter.load(path).validation.error_codes == (code,)


def test_load_of_a_folder_is_unreadable(adapter: TomlUserDataFile, path: Path) -> None:
    path.mkdir(parents=True)

    assert adapter.load(path).validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_UNREADABLE,)


def test_save_replaces_the_file_keeps_bak_and_makes_the_daily_copy(
    adapter: TomlUserDataFile, path: Path, clock: FakeClock, tmp_path: Path
) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    before = path.read_bytes()
    clock.advance(seconds=10)

    outcome = _save(adapter, path, make_user_data(LanguageEnum.FRENCH))

    assert outcome.validation.is_success
    assert outcome.revision == 7
    assert outcome.saved_at == clock.now_utc()
    assert adapter.load(path).is_success
    assert _side(path, ".bak").read_bytes() == before
    assert (tmp_path / "backups" / "concentrator-2026-11-06.toml").is_file()


def test_save_after_a_hand_edit_writes_nothing(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    edited = path.read_bytes().replace(b"language = 1", b"language = 2")
    path.write_bytes(edited)

    outcome = _save(adapter, path, make_user_data(LanguageEnum.ENGLISH))

    assert outcome.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)
    assert outcome.saved_at is None
    assert path.read_bytes() == edited
    assert not _side(path, ".tmp").exists()


def test_keep_concentrator_version_overwrites_and_keeps_the_edit_in_bak(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    edited = path.read_bytes().replace(b"language = 1", b"language = 2")
    path.write_bytes(edited)

    outcome = _save(adapter, path, make_user_data(LanguageEnum.ENGLISH), overwrite=True)
    following = _save(adapter, path, make_user_data(LanguageEnum.FRENCH))

    assert outcome.validation.is_success
    assert following.validation.is_success
    assert b"language = 2" in path.read_bytes()
    assert b"language = 1" in _side(path, ".bak").read_bytes()


def test_reload_after_a_hand_edit_makes_the_next_save_pass(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    path.write_bytes(path.read_bytes().replace(b"language = 1", b"language = 2"))

    reloaded = adapter.load(path)
    outcome = _save(adapter, path, make_user_data(LanguageEnum.ENGLISH))

    assert reloaded.data is not None
    assert reloaded.data.data.settings.language is LanguageEnum.FRENCH
    assert outcome.validation.is_success


def test_touched_but_identical_file_saves(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data())
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 3_000_000_000))

    assert _save(adapter, path, make_user_data(LanguageEnum.ENGLISH)).validation.is_success


def test_probe_reports_main_tmp_and_bak(adapter: TomlUserDataFile, path: Path, clock: FakeClock) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    clock.advance(seconds=5)
    _save(adapter, path, make_user_data(LanguageEnum.FRENCH))
    _side(path, ".tmp").write_text("{ broken", encoding="utf-8")

    report = adapter.probe(path).data

    assert report is not None
    assert report.main.state is FileStateEnum.VALID
    assert report.main.saved_at == clock.now_utc()
    assert report.backup.state is FileStateEnum.VALID
    assert report.temporary.state is FileStateEnum.INVALID
    assert report.temporary.validation.error_codes == (ErrorCodeEnum.STORAGE_SYNTAX_INVALID,)
    assert report.probe_of(RecoverySourceEnum.BACKUP) is report.backup


def test_restore_newer_tmp_over_a_valid_main(adapter: TomlUserDataFile, path: Path, clock: FakeClock) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    old_main = path.read_bytes()
    _side(path, ".tmp").write_text(CODEC.encode(make_stored(LanguageEnum.FRENCH, clock.now_utc())), encoding="utf-8")
    clock.advance(seconds=30)

    restored = adapter.restore(path, RecoverySourceEnum.TEMPORARY)

    assert restored.data is not None
    assert restored.data.data.settings.language is LanguageEnum.FRENCH
    assert restored.data.saved_at == clock.now_utc()
    assert not _side(path, ".tmp").exists()
    assert _side(path, ".bak").read_bytes() == old_main


def test_restore_bak_quarantines_a_damaged_main_and_keeps_bak(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))
    _save(adapter, path, make_user_data(LanguageEnum.FRENCH))
    backup_bytes = _side(path, ".bak").read_bytes()
    path.write_text("{ damaged", encoding="utf-8")

    restored = adapter.restore(path, RecoverySourceEnum.BACKUP)

    assert restored.data is not None
    assert restored.data.data.settings.language is LanguageEnum.ENGLISH
    assert _side(path, ".bak").read_bytes() == backup_bytes
    assert _side(path, ".corrupt-20261106-100000").read_text(encoding="utf-8") == "{ damaged"


def test_restore_refuses_an_invalid_candidate_and_changes_nothing(adapter: TomlUserDataFile, path: Path) -> None:
    path.parent.mkdir(parents=True)
    path.write_text("{ damaged", encoding="utf-8")
    _side(path, ".bak").write_text("{ also damaged", encoding="utf-8")

    result = adapter.restore(path, RecoverySourceEnum.BACKUP)

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_SYNTAX_INVALID,)
    assert path.read_text(encoding="utf-8") == "{ damaged"


def test_restore_from_an_unknown_source_fails(adapter: TomlUserDataFile, path: Path) -> None:
    assert adapter.restore(path, RecoverySourceEnum.UNSET).validation.error_codes == (ErrorCodeEnum.ENUM_VALUE_UNKNOWN,)


def test_quarantine_and_discard_rename_with_a_local_stamp(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data())
    _side(path, ".tmp").write_text("stale", encoding="utf-8")

    discarded = adapter.discard_temporary(path)
    quarantined = adapter.quarantine(path)

    assert discarded.data == _side(path, ".tmp.discarded-20261106-100000").as_posix()
    assert quarantined.data == _side(path, ".corrupt-20261106-100000").as_posix()
    assert not path.exists()
    assert not _side(path, ".tmp").exists()


def test_rename_failures(adapter: TomlUserDataFile, path: Path) -> None:
    missing = adapter.quarantine(path)
    path.parent.mkdir(parents=True)
    path.write_text("x", encoding="utf-8")
    _side(path, ".corrupt-20261106-100000").write_text("taken", encoding="utf-8")

    taken = adapter.quarantine(path)

    assert missing.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_NOT_FOUND,)
    assert taken.validation.error_codes == (ErrorCodeEnum.STORAGE_REPLACE_FAILED,)


def test_blocking_write_times_out_while_the_writer_is_busy(
    tmp_path: Path, writer: WriterThread, clock: FakeClock, path: Path
) -> None:
    adapter = TomlUserDataFile(
        codec=CODEC,
        writer=writer,
        clock=clock,
        storage=make_storage_section(blocking_write_timeout_ms=50),
        backup_dir=tmp_path / "backups",
    )
    release = threading.Event()
    writer.submit(lambda: release.wait(TIMEOUT_MS / 1000), False, lambda _result: None)

    try:
        result = adapter.create(path, make_user_data())
    finally:
        release.set()

    assert result.validation.error_codes == (ErrorCodeEnum.STORAGE_FLUSH_TIMEOUT,)
    assert writer.flush(TIMEOUT_MS).is_success


def test_blocking_save_returns_the_outcome_and_checks_external_changes(adapter: TomlUserDataFile, path: Path) -> None:
    adapter.create(path, make_user_data(LanguageEnum.ENGLISH))

    saved = adapter.save(path, make_user_data(LanguageEnum.FRENCH), 3, timeout_ms=TIMEOUT_MS)
    path.write_bytes(path.read_bytes().replace(b"language = 2", b"language = 1"))
    refused = adapter.save(path, make_user_data(LanguageEnum.FRENCH), 4, timeout_ms=TIMEOUT_MS)
    forced = adapter.save(path, make_user_data(LanguageEnum.FRENCH), 4, timeout_ms=TIMEOUT_MS, overwrite_external=True)

    assert saved.revision == 3
    assert saved.validation.is_success
    assert saved.saved_at is not None
    assert refused.validation.error_codes == (ErrorCodeEnum.STORAGE_FILE_CHANGED_EXTERNALLY,)
    assert forced.validation.is_success
    assert b"language = 2" in path.read_bytes()


def test_blocking_save_times_out_behind_a_busy_writer(
    adapter: TomlUserDataFile, writer: WriterThread, path: Path
) -> None:
    release = threading.Event()
    writer.submit(lambda: release.wait(TIMEOUT_MS / 1000), False, lambda _result: None)

    try:
        outcome = adapter.save(path, make_user_data(), 5, timeout_ms=50)
    finally:
        release.set()

    assert outcome.revision == 5
    assert outcome.saved_at is None
    assert outcome.validation.error_codes == (ErrorCodeEnum.STORAGE_FLUSH_TIMEOUT,)
    assert writer.flush(TIMEOUT_MS).is_success
