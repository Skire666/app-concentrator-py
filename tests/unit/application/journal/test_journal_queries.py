import logging

from concentrator.application.journal.journal_queries import JournalQueries, JournalRecord
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from tests.fakes.fake_log_feed import FakeLogFeed


def test_records_since_converts_the_newer_entries() -> None:
    feed = FakeLogFeed()
    feed.log("old")
    entry = feed.log("Save failed", logging.ERROR, source="concentrator.storage", thread="writer")

    records = JournalQueries(feed).records_since(1)

    assert records == (
        JournalRecord(
            sequence=2,
            created_at=entry.created_at,
            level=LogLevelEnum.ERROR,
            source="concentrator.storage",
            thread="writer",
            message="Save failed",
        ),
    )


def test_error_count_comes_from_the_feed() -> None:
    feed = FakeLogFeed()
    feed.log("a", logging.CRITICAL)
    feed.log("b", logging.WARNING)

    assert JournalQueries(feed).error_count() == 1
