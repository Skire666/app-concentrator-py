import pytest

from concentrator.domain.common.base_int_enum import UNKNOWN_VALUE, UNSET_VALUE, BaseIntEnum
from tests.architecture.source_tree import PACKAGE_NAME, import_all_modules


def _application_enums() -> list[type[BaseIntEnum]]:
    import_all_modules()
    found: list[type[BaseIntEnum]] = []
    pending: list[type[BaseIntEnum]] = list(BaseIntEnum.__subclasses__())
    while pending:
        enum_class = pending.pop()
        pending.extend(enum_class.__subclasses__())
        if enum_class.__module__.startswith(f"{PACKAGE_NAME}."):
            found.append(enum_class)
    return sorted(found, key=lambda enum_class: enum_class.__qualname__)


ENUMS = _application_enums()


def test_enum_discovery_finds_the_kernel_enums() -> None:
    names = {enum_class.__name__ for enum_class in ENUMS}

    assert {"SeverityEnum", "ErrorCodeEnum", "ErrorCategoryEnum", "LanguageEnum"} <= names


@pytest.mark.parametrize("enum_class", ENUMS, ids=lambda enum_class: enum_class.__name__)
def test_enum_defines_unknown_and_unset(enum_class: type[BaseIntEnum]) -> None:
    members = enum_class.__members__

    assert "UNKNOWN" in members
    assert "UNSET" in members
    assert members["UNKNOWN"].value == UNKNOWN_VALUE
    assert members["UNSET"].value == UNSET_VALUE


@pytest.mark.parametrize("enum_class", ENUMS, ids=lambda enum_class: enum_class.__name__)
def test_enum_is_named_and_placed_by_convention(enum_class: type[BaseIntEnum]) -> None:
    assert enum_class.__name__.endswith("Enum")
    assert enum_class.__module__.endswith("_enum")


@pytest.mark.parametrize("enum_class", ENUMS, ids=lambda enum_class: enum_class.__name__)
def test_enum_values_are_not_reused(enum_class: type[BaseIntEnum]) -> None:
    assert len(enum_class.__members__) == len(enum_class)
