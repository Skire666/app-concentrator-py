"""One step of the data file migrations: a parsed document of one schema version to the next."""

from collections.abc import Callable
from dataclasses import dataclass

type Document = dict[str, object]
"""Parsed TOML document, before pydantic validation."""


@dataclass(frozen=True, slots=True, kw_only=True)
class SchemaMigration:
    """Turns a document of ``from_version`` into a document of ``from_version + 1``.

    A step only moves, renames or fills in keys. It must accept any structure: a value it does not
    recognize is passed through unchanged, and the schema validation that follows reports it. It never
    changes ``schema_version``: ``MigrationChain`` sets it after the step.

    Attributes:
        from_version: Schema version the step reads.
        migrate: Pure function returning a new document (its argument is never changed).
    """

    from_version: int
    migrate: Callable[[Document], Document]

    @property
    def to_version(self) -> int:
        """Schema version of the document the step returns."""
        return self.from_version + 1
