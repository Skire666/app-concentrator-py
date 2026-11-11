import logging
from dataclasses import replace
from datetime import UTC, datetime
from typing import Final

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.user_data import StoredUserData
from concentrator.domain.focus.focus_item import FocusItem, FocusItemId
from concentrator.domain.focus.focus_items_collection import FocusItemsCollection
from concentrator.domain.todo.task import TaskId
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.tasks_collection import TasksCollection
from concentrator.infrastructure.persistence.store_focus import StoreFocusItemReader, StoreFocusItemWriter
from concentrator.infrastructure.persistence.user_data_codec import UserDataCodec
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.focus_factory import make_item
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.todo_factory import SPEC_LIST_ID, SPEC_TASK_ID, make_task
from tests.fakes.user_data_factory import USER_DATA_LIMITS, make_stored, make_user_data

CODEC: Final = UserDataCodec("0.1.0", USER_DATA_LIMITS)
QUEUED_AT: Final = datetime(2026, 11, 6, 17, 10, tzinfo=UTC)
SPEC_ITEM_ID: Final = FocusItemId("019a5c30-cccc-7ddd-8eee-5a6b7c8d9e0f")

SPEC_FOCUS_TEXT: Final = """
[[focus_queue]]
id = '019a5c30-cccc-7ddd-8eee-5a6b7c8d9e0f'
created_at = '2026-11-06T17:10:00Z'
updated_at = '2026-11-06T17:10:00Z'
task_id = '019a5c22-bbbb-7ccc-8ddd-4f5a6b7c8d9e'
position = 0
"""


def _stored(*items: FocusItem, state: TaskStateEnum = TaskStateEnum.OPEN) -> StoredUserData:
    stored = make_stored()
    task = replace(make_task(1, list_id=SPEC_LIST_ID, state=state), id=SPEC_TASK_ID)
    data = stored.data.with_tasks(TasksCollection((task,))).with_focus_queue(FocusItemsCollection(items))
    return replace(stored, data=data)


def _spec_item(position: int = 0) -> FocusItem:
    return FocusItem.create(SPEC_ITEM_ID, QUEUED_AT, task_id=SPEC_TASK_ID, position=position)


def test_queue_is_written_as_in_the_spec_example() -> None:
    text = CODEC.encode(_stored(_spec_item()))

    assert text.endswith(SPEC_FOCUS_TEXT)
    assert "focus_queue = []" not in text


def test_empty_queue_is_written_as_an_empty_array() -> None:
    assert "\nfocus_queue = []\n" in CODEC.encode(_stored())


def test_queue_round_trips() -> None:
    stored = _stored(_spec_item())

    assert CODEC.decode(CODEC.encode(stored)).data == stored


def test_file_without_a_queue_reads_none() -> None:
    text = CODEC.encode(_stored()).replace("focus_queue = []\n", "")

    decoded = CODEC.decode(text)

    assert decoded.data is not None
    assert decoded.data.data.focus_queue is None


def test_item_of_a_missing_task_is_dropped_with_a_warning(caplog: pytest.LogCaptureFixture) -> None:
    dangling = FocusItem.create(FocusItemId("item-x"), QUEUED_AT, task_id=TaskId("task-gone"), position=0)
    text = CODEC.encode(_stored(dangling, _spec_item(position=1)))

    with caplog.at_level(logging.WARNING):
        decoded = CODEC.decode(text)

    assert decoded.data is not None
    assert decoded.data.data.focus_queue == FocusItemsCollection((_spec_item(position=0),))
    assert "Focus item focus_queue.0 (item-x) of the data file ignored: FOCUS_TASK_MISSING" in caplog.text


def test_item_of_a_done_task_is_dropped(caplog: pytest.LogCaptureFixture) -> None:
    text = CODEC.encode(_stored(_spec_item(), state=TaskStateEnum.DONE))

    with caplog.at_level(logging.WARNING):
        decoded = CODEC.decode(text)

    assert decoded.data is not None
    assert decoded.data.data.focus_queue == FocusItemsCollection()
    assert "FOCUS_TASK_NOT_OPEN" in caplog.text


def test_store_reader_and_writer_use_the_queue_section() -> None:
    store = _store_with_queue()
    reader = StoreFocusItemReader(store)
    writer = StoreFocusItemWriter(store)

    created = writer.create(make_item(3))
    moved = writer.update_many([replace(make_item(1), position=9)])
    removed = writer.delete_many(["item-002"])

    assert created.is_success
    assert moved.is_success
    assert removed.is_success
    assert [item.id for item in reader.all_items().value_or(FocusItemsCollection()).ordered()] == [
        "item-003",
        "item-001",
    ]
    assert reader.exists("item-001").data is True
    assert reader.read_item("item-001").is_success
    assert len(reader.find(_AllItems()).value_or(FocusItemsCollection())) == 2


def test_store_reader_reads_an_empty_queue_before_completion() -> None:
    store = UserDataStore(EventBus(RecordingErrorReporter()))
    store.reset(replace(make_user_data(), focus_queue=None))

    assert len(StoreFocusItemReader(store).all_items().value_or(FocusItemsCollection((make_item(1),)))) == 0


class _AllItems:
    def matches(self, entity: FocusItem) -> bool:
        return bool(entity.id)


def _store_with_queue() -> UserDataStore:
    store = UserDataStore(EventBus(RecordingErrorReporter()))
    store.reset(make_user_data().with_focus_queue(FocusItemsCollection((make_item(1), make_item(2)))))
    return store
