"""Writes the timer favorites (generic write operations)."""

from typing import Protocol

from concentrator.application.ports.entity_writer_port import EntityWriterPort
from concentrator.domain.timer.timer_preset import TimerPreset


class TimerPresetWriterPort(EntityWriterPort[TimerPreset], Protocol):
    """Write side of the favorites: ``create``, ``update``, ``delete``, ``copy_business``, ``copy_technical``."""
