from pathlib import Path

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.infrastructure.system.builtin_sound_catalog import BuiltinSoundCatalog


@pytest.fixture
def sounds(tmp_path: Path) -> Path:
    folder = tmp_path / "sounds"
    folder.mkdir()
    for name in ("alarm-soft.mp3", "alarm-classic.MP3", "notes.txt"):
        (folder / name).write_bytes(b"ID3")
    (folder / "nested.mp3").mkdir()
    return folder


def test_builtin_sounds_are_the_mp3_stems_sorted(sounds: Path) -> None:
    catalog = BuiltinSoundCatalog(sounds)

    names = [sound.value for sound in catalog.builtin_sounds()]

    assert names == ["alarm-classic", "alarm-soft", "nested"]


def test_missing_folder_lists_nothing_with_a_warning(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    assert BuiltinSoundCatalog(tmp_path / "absent").builtin_sounds() == ()
    assert "Cannot list the built-in sounds" in caplog.text


def test_builtin_sound_resolves_to_its_file(sounds: Path) -> None:
    result = BuiltinSoundCatalog(sounds).resolve(SoundRef.builtin("alarm-soft"))

    assert result.data == (sounds / "alarm-soft.mp3").as_posix()


def test_existing_file_resolves_as_given(sounds: Path) -> None:
    path = (sounds / "notes.txt").as_posix()

    assert BuiltinSoundCatalog(sounds).resolve(SoundRef.file(path)).data == path


@pytest.mark.parametrize(
    "sound",
    [
        SoundRef.builtin("alarm-missing"),
        SoundRef.builtin("../sounds/alarm-soft"),
        SoundRef.builtin("nested"),
        SoundRef.builtin(""),
        SoundRef.file("Z:/nowhere/alarm.mp3"),
        SoundRef.file(""),
        SoundRef(kind=SoundKindEnum.UNSET, value="alarm-soft"),
        SoundRef(kind=SoundKindEnum.UNKNOWN, value="alarm-soft"),
    ],
)
def test_unresolvable_sounds_are_not_found(sounds: Path, sound: SoundRef) -> None:
    result = BuiltinSoundCatalog(sounds).resolve(sound)

    assert result.validation.error_codes == (ErrorCodeEnum.AUDIO_FILE_NOT_FOUND,)


def test_every_shipped_sound_resolves() -> None:
    catalog = BuiltinSoundCatalog(AppPaths.from_runtime().sounds_dir)

    shipped = catalog.builtin_sounds()

    assert shipped
    assert all(catalog.resolve(sound).is_success for sound in shipped)
