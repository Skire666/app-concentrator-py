from concentrator.application.timer.chime_defaults import ChimeDefaults
from concentrator.domain.timer.chime_settings import ChimeSettings
from concentrator.domain.timer.sound_ref import SoundRef
from concentrator.domain.timer.volume import Volume
from tests.fakes.app_config_factory import make_chime_section


def test_chime_defaults_come_from_the_ini_section() -> None:
    defaults = ChimeDefaults.from_section(make_chime_section(default_enabled=True, default_volume=35))

    assert defaults.enabled is True
    assert defaults.settings == ChimeSettings(
        sound=SoundRef.builtin("chime"), volume=Volume(35), start_hour=8, end_hour=20
    )
    assert defaults.fallback_sound == SoundRef.builtin("chime")
    assert defaults.trigger_window_seconds == 59
