"""Reference to an alarm or chime sound."""

from dataclasses import dataclass
from typing import Final, Self

from concentrator.domain.timer.sound_kind_enum import SoundKindEnum

_WINDOWS_SEPARATOR: Final = "\\"
_SEPARATOR: Final = "/"


@dataclass(frozen=True, slots=True, kw_only=True)
class SoundRef:
    """A built-in sound (by name) or an audio file (by path).

    Use the factories: they normalize the value (trimmed, and ``/`` separators in paths). Whether the
    sound exists is checked outside the domain, when it is chosen and when it plays.

    Attributes:
        kind: Built-in or file.
        value: Built-in sound name (file stem in ``assets/sounds``) or file path with ``/`` separators.
    """

    kind: SoundKindEnum
    value: str

    @classmethod
    def builtin(cls, name: str) -> Self:
        """Reference a built-in sound.

        Args:
            name: Sound name, for example ``alarm-classic``.

        Returns:
            The reference.
        """
        return cls(kind=SoundKindEnum.BUILTIN, value=name.strip())

    @classmethod
    def file(cls, path: str) -> Self:
        """Reference an audio file.

        Args:
            path: File path, with ``/`` or Windows separators.

        Returns:
            The reference, with ``/`` separators.
        """
        return cls(kind=SoundKindEnum.FILE, value=path.strip().replace(_WINDOWS_SEPARATOR, _SEPARATOR))

    @classmethod
    def of(cls, kind: SoundKindEnum, value: str) -> Self:
        """Rebuild a reference read from storage, normalized like the factories.

        Args:
            kind: Stored kind (may be ``UNKNOWN`` or ``UNSET``; the rules reject it).
            value: Stored value.

        Returns:
            The reference.
        """
        if kind is SoundKindEnum.FILE:
            return cls.file(value)
        return cls(kind=kind, value=value.strip())
