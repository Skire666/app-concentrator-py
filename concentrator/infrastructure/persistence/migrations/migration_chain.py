"""Ordered schema migrations, from any supported version up to the version of this application."""

import logging
from collections.abc import Sequence
from typing import Final

from concentrator.infrastructure.persistence.migrations.schema_migration import Document, SchemaMigration

_logger = logging.getLogger(__name__)

SCHEMA_VERSION_FIELD: Final = "schema_version"
_GAP: Final = "Migration steps must follow each other up to version {target}: {versions}"


def schema_version_of(document: Document) -> int | None:
    """Read the schema version of a parsed document.

    Args:
        document: Parsed TOML document.

    Returns:
        The version, or ``None`` when it is absent or not an integer (left to the schema validation).
    """
    version = document.get(SCHEMA_VERSION_FIELD)
    if isinstance(version, int) and not isinstance(version, bool):
        return version
    return None


class MigrationChain:
    """Runs the steps that bring an older document up to ``target_version``.

    Schema version 1 is the first released layout, so the production chain has no step. A later breaking
    change bumps ``CURRENT_SCHEMA_VERSION`` and appends one step (ADR-044).
    """

    def __init__(self, target_version: int, steps: Sequence[SchemaMigration] = ()) -> None:
        """Create the chain.

        Args:
            target_version: Schema version this application reads and writes.
            steps: One step per version just below the target, in any order.

        Raises:
            ValueError: The steps do not follow each other up to ``target_version`` (programming error).
        """
        ordered = tuple(sorted(steps, key=lambda step: step.from_version))
        versions = [step.from_version for step in ordered]
        if versions != list(range(target_version - len(ordered), target_version)):
            raise ValueError(_GAP.format(target=target_version, versions=versions))
        self._target_version = target_version
        self._steps = {step.from_version: step for step in ordered}

    @property
    def target_version(self) -> int:
        """Schema version this application reads and writes."""
        return self._target_version

    def upgrade(self, document: Document) -> Document:
        """Bring a document up to the target version.

        Args:
            document: Parsed TOML document, not newer than the target (checked before).

        Returns:
            The migrated document; unchanged when it is current, has no usable version, or is older than
            the first step (the schema validation then reports the version).
        """
        first = schema_version_of(document)
        if first is None or first not in self._steps:
            return document
        version = first
        while version in self._steps:
            step = self._steps[version]
            document = {**step.migrate(document), SCHEMA_VERSION_FIELD: step.to_version}
            version = step.to_version
        _logger.info("Data file migrated from schema version %d to %d", first, version)
        return document
