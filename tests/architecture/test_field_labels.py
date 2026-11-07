"""Every field of the user data file has a ``field.<path>`` label in both catalogs (``AGENTS.md`` section 10).

The paths come from the pydantic DTOs, so a later phase that adds a section cannot forget its labels.
"""

import json
import types
import typing
from typing import Final, cast

import pytest
from pydantic import BaseModel

from concentrator.infrastructure.persistence.schemas.user_data_schema import UserDataSchema
from concentrator.presentation.storage.storage_messages import field_label_key
from tests.architecture.source_tree import REPO_ROOT

CATALOG_DIR: Final = REPO_ROOT / "assets" / "i18n"


def _model_in(annotation: object) -> type[BaseModel] | None:
    """The DTO class inside a field annotation (directly, in a list, or in an optional)."""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for argument in typing.get_args(annotation):
        found = _model_in(argument)
        if found is not None:
            return found
    if isinstance(annotation, types.UnionType):
        return None
    return None


def _field_paths(model: type[BaseModel], prefix: str = "") -> list[str]:
    paths: list[str] = []
    for name, info in model.model_fields.items():
        path = f"{prefix}.{name}" if prefix else name
        paths.append(path)
        nested = _model_in(info.annotation)
        if nested is not None:
            paths.extend(_field_paths(nested, path))
    return paths


FIELD_PATHS: Final = _field_paths(UserDataSchema)


def _catalog(name: str) -> dict[str, str]:
    return cast("dict[str, str]", json.loads((CATALOG_DIR / name).read_text(encoding="utf-8")))


def test_schema_walk_finds_the_nested_settings_fields() -> None:
    assert {"schema_version", "settings", "settings.language"} <= set(FIELD_PATHS)


@pytest.mark.parametrize("catalog", ["en.json", "fr.json"])
@pytest.mark.parametrize("path", FIELD_PATHS)
def test_every_file_field_has_a_label(catalog: str, path: str) -> None:
    assert field_label_key(path) in _catalog(catalog)
