import logging

import pytest

from concentrator.infrastructure.persistence.migrations.migration_chain import MigrationChain, schema_version_of
from concentrator.infrastructure.persistence.migrations.schema_migration import Document, SchemaMigration


def _step(from_version: int, old: str, new: str) -> SchemaMigration:
    def migrate(document: Document) -> Document:
        moved = {key: value for key, value in document.items() if key != old}
        if old in document:
            moved[new] = document[old]
        return moved

    return SchemaMigration(from_version=from_version, migrate=migrate)


def test_schema_version_of_reads_integers_only() -> None:
    assert schema_version_of({"schema_version": 3}) == 3
    assert schema_version_of({"schema_version": True}) is None
    assert schema_version_of({"schema_version": "1"}) is None
    assert schema_version_of({}) is None


def test_step_to_version_is_the_next_version() -> None:
    assert _step(4, "a", "b").to_version == 5


def test_chain_without_step_leaves_a_current_document_unchanged() -> None:
    document: Document = {"schema_version": 1, "tasks": []}

    assert MigrationChain(1).upgrade(document) is document


def test_chain_runs_every_step_in_order_and_sets_the_version(caplog: pytest.LogCaptureFixture) -> None:
    chain = MigrationChain(3, (_step(2, "b", "c"), _step(1, "a", "b")))
    original: Document = {"schema_version": 1, "a": [1]}

    with caplog.at_level(logging.INFO):
        upgraded = chain.upgrade(original)

    assert upgraded == {"schema_version": 3, "c": [1]}
    assert original == {"schema_version": 1, "a": [1]}
    assert "Data file migrated from schema version 1 to 3" in caplog.text


def test_chain_starts_at_the_version_of_the_document() -> None:
    chain = MigrationChain(3, (_step(1, "a", "b"), _step(2, "b", "c")))

    assert chain.upgrade({"schema_version": 2, "b": 0}) == {"schema_version": 3, "c": 0}


@pytest.mark.parametrize("version", [None, 0, 3])
def test_chain_leaves_unusable_or_current_versions_to_the_validation(version: int | None) -> None:
    document: Document = {"a": 1} if version is None else {"schema_version": version, "a": 1}

    assert MigrationChain(3, (_step(1, "a", "b"), _step(2, "b", "c"))).upgrade(document) is document


@pytest.mark.parametrize(
    "versions", [(1,), (2, 2), (0, 2), (3,)], ids=["ends-before-target", "duplicate", "gap", "beyond-target"]
)
def test_chain_refuses_steps_that_do_not_reach_the_target(versions: tuple[int, ...]) -> None:
    with pytest.raises(ValueError, match="up to version 3"):
        MigrationChain(3, tuple(_step(version, "a", "b") for version in versions))
