"""Inline error shown under a form field."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldErrorSnapshot:
    """A translated message attached to one field.

    Attributes:
        field: Dotted field path, ``""`` for a form-level message.
        message: Translated message.
    """

    field: str
    message: str
