"""Sound player, sound catalog and attention fakes."""

from typing import override

from concentrator.application.ports.attention_port import AttentionPort
from concentrator.application.ports.sound_catalog_port import SoundCatalogPort
from concentrator.application.ports.sound_player_port import SoundPlayback, SoundPlayerPort
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.sound_kind_enum import SoundKindEnum
from concentrator.domain.timer.sound_ref import SoundRef

SOUNDS_DIR = "C:/app/assets/sounds"


class FakeSoundPlayer(SoundPlayerPort):
    """Records ``played`` playbacks and ``stops``; ``play_failure`` and ``check_results`` script answers."""

    def __init__(self) -> None:
        self.played: list[SoundPlayback] = []
        self.stops = 0
        self.play_failure: ValidationResult | None = None
        self.check_results: dict[str, ValidationResult] = {}

    @property
    def last(self) -> SoundPlayback:
        return self.played[-1]

    @override
    def play(self, playback: SoundPlayback) -> ValidationResult:
        self.played.append(playback)
        return self.play_failure or ValidationResult.success()

    @override
    def stop(self) -> None:
        self.stops += 1

    @override
    def check(self, path: str) -> ValidationResult:
        return self.check_results.get(path, ValidationResult.success())


class FakeSoundCatalog(SoundCatalogPort):
    """Built-in sounds live in ``SOUNDS_DIR``; files exist when listed in ``existing_files``."""

    def __init__(self, builtin: tuple[str, ...] = ("alarm-classic", "alarm-soft")) -> None:
        self.builtin = builtin
        self.existing_files: set[str] = set()

    @override
    def builtin_sounds(self) -> tuple[SoundRef, ...]:
        return tuple(SoundRef.builtin(name) for name in sorted(self.builtin))

    @override
    def resolve(self, sound: SoundRef) -> DataResult[str]:
        if sound.kind is SoundKindEnum.BUILTIN and sound.value in self.builtin:
            return DataResult.ok(f"{SOUNDS_DIR}/{sound.value}.mp3")
        if sound.kind is SoundKindEnum.FILE and sound.value in self.existing_files:
            return DataResult.ok(sound.value)
        return DataResult.fail(ValidationResult.failure(ErrorCodeEnum.AUDIO_FILE_NOT_FOUND))


class FakeAttention(AttentionPort):
    """``active`` is the application state; counts ``attention_requests``."""

    def __init__(self, *, active: bool = False) -> None:
        self.active = active
        self.attention_requests = 0

    @override
    def is_application_active(self) -> bool:
        return self.active

    @override
    def request_attention(self) -> None:
        self.attention_requests += 1
