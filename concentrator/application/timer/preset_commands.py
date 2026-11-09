"""Write use cases of the timer favorites."""

import logging

from concentrator.application.common.event_bus import EventBus
from concentrator.application.ports.clock_port import ClockPort
from concentrator.application.ports.id_generator_port import IdGeneratorPort
from concentrator.application.ports.timer_preset_reader_port import TimerPresetReaderPort
from concentrator.application.ports.timer_preset_writer_port import TimerPresetWriterPort
from concentrator.application.timer.timer_commands import TimerCommands
from concentrator.application.timer.timer_events import TimerPresetsChangedEvent
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.timer.duration import Duration
from concentrator.domain.timer.timer_limits import TimerLimits
from concentrator.domain.timer.timer_preset import TimerPreset, TimerPresetId
from concentrator.domain.timer.timer_preset_rules import TimerPresetRules
from concentrator.domain.timer.timer_presets_collection import TimerPresetsCollection

_logger = logging.getLogger(__name__)


class PresetCommands:
    """Create, update, delete, move a favorite, and start the timer with one (``apply_and_start``).

    Each successful change publishes one ``TimerPresetsChangedEvent``. Labels never reach the log.
    """

    def __init__(
        self,
        *,
        reader: TimerPresetReaderPort,
        writer: TimerPresetWriterPort,
        timer: TimerCommands,
        ids: IdGeneratorPort,
        clock: ClockPort,
        event_bus: EventBus,
        limits: TimerLimits,
    ) -> None:
        """Create the use cases.

        Args:
            reader: Favorites reader.
            writer: Favorites writer.
            timer: Stores the duration and starts the countdown.
            ids: Ids of new favorites.
            clock: Change instants.
            event_bus: Receives ``TimerPresetsChangedEvent``.
            limits: Bounds from ``concentrator.ini``.
        """
        self._reader = reader
        self._writer = writer
        self._timer = timer
        self._ids = ids
        self._clock = clock
        self._event_bus = event_bus
        self._limits = limits

    def create(self, label: str, duration: Duration) -> DataResult[TimerPreset]:
        """Add a favorite after the last one.

        Args:
            label: Label as typed (``""`` for the automatic label).
            duration: Countdown duration.

        Returns:
            The stored favorite, or the rule failures (``PRESET_LIMIT_REACHED``,
            ``PRESET_DURATION_DUPLICATE``, label and duration rules).
        """
        presets = self._presets()
        preset = TimerPreset.create(
            TimerPresetId(self._ids.new_id()),
            self._clock.now_utc(),
            label=label,
            duration=duration,
            position=presets.next_position(),
        )
        validation = TimerPresetRules.validate_room(presets, self._limits).merge(
            TimerPresetRules.validate(preset, self._limits),
            TimerPresetRules.validate_unique_duration(presets, duration),
        )
        if validation.is_failure:
            return DataResult.fail(validation)
        return self._published(self._writer.create(preset), "created")

    def update(self, preset_id: str, label: str, duration: Duration) -> DataResult[TimerPreset]:
        """Change the label and the duration of a favorite.

        Args:
            preset_id: Favorite to change.
            label: Label as typed.
            duration: New duration.

        Returns:
            The stored favorite (unchanged values are not written), ``ENTITY_NOT_FOUND`` or the rule
            failures.
        """
        current = self._reader.read_item(preset_id)
        if current.data is None:
            return current
        changed = current.data.with_values(label, duration, self._clock.now_utc())
        if (changed.label, changed.duration) == (current.data.label, current.data.duration):
            return current
        validation = TimerPresetRules.validate(changed, self._limits).merge(
            TimerPresetRules.validate_unique_duration(self._presets(), duration, except_id=preset_id)
        )
        if validation.is_failure:
            return DataResult.fail(validation)
        return self._published(self._writer.update(changed), "updated")

    def delete(self, preset_id: str) -> ValidationResult:
        """Remove a favorite.

        Args:
            preset_id: Favorite to remove.

        Returns:
            Success or ``ENTITY_NOT_FOUND``.
        """
        return self._published(self._writer.delete(preset_id), "deleted").validation

    def move(self, preset_id: str, offset: int) -> ValidationResult:
        """Move a favorite one place earlier (``-1``) or later (``+1``).

        Args:
            preset_id: Favorite to move.
            offset: Direction.

        Returns:
            Success, skipped when it is already at that end, or ``ENTITY_NOT_FOUND``.
        """
        moved = self._presets().moved(preset_id, offset, self._clock.now_utc())
        if moved.data is None:
            return moved.validation
        for preset in moved.data:
            written = self._writer.update(preset)
            if written.data is None:
                return written.validation
        _logger.info("Timer favorite moved")
        self._event_bus.publish(TimerPresetsChangedEvent(presets=self._presets()))
        return ValidationResult.success()

    def apply_and_start(self, preset_id: str) -> ValidationResult:
        """Make a favorite's duration the timer duration and start the countdown (one click, ``IDLE`` only).

        Args:
            preset_id: Favorite clicked.

        Returns:
            Success, ``ENTITY_NOT_FOUND``, or ``TIMER_TRANSITION_INVALID`` when the timer is not ``IDLE``
            (the configuration is then unchanged).
        """
        preset = self._reader.read_item(preset_id)
        if preset.data is None:
            return preset.validation
        return self._timer.start_with_duration(preset.data.duration)

    def _presets(self) -> TimerPresetsCollection:
        """Return the current favorites.

        Returns:
            The favorites (the in-memory read cannot fail; empty if it ever did).
        """
        return self._reader.all_items().value_or(TimerPresetsCollection())

    def _published(self, written: DataResult[TimerPreset], change: str) -> DataResult[TimerPreset]:
        """Publish the change of a successful write.

        Args:
            written: Writer result.
            change: What happened, for the log.

        Returns:
            The writer result.
        """
        if written.data is not None:
            _logger.info("Timer favorite %s", change)
            self._event_bus.publish(TimerPresetsChangedEvent(presets=self._presets()))
        return written
