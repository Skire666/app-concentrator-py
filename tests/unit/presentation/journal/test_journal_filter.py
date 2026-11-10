import logging

from concentrator.application.journal.journal_queries import JournalRecord
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.journal.journal_filter import ALL_LEVELS, JournalEntry, JournalFilter
from tests.fakes.fake_log_feed import FakeLogFeed


def _entries(*specs: tuple[str, int]) -> list[JournalEntry]:
    feed = FakeLogFeed()
    for message, level in specs:
        feed.log(message, level)
    return [JournalEntry.of(JournalRecord.from_entry(entry)) for entry in feed.entries]


ENTRIES = _entries(
    ("État du minuteur", logging.INFO),
    ("debug detail", logging.DEBUG),
    ("Save failed", logging.ERROR),
    ("timer started", logging.INFO),
)


def _messages(entries: tuple[JournalEntry, ...]) -> list[str]:
    return [entry.record.message for entry in entries]


def test_default_filter_shows_everything_and_follows() -> None:
    journal_filter = JournalFilter()

    assert _messages(journal_filter.visible(ENTRIES)) == [entry.record.message for entry in ENTRIES]
    assert journal_filter.follow
    assert not journal_filter.is_paused
    assert set(journal_filter.levels) == set(ALL_LEVELS)


def test_level_toggles_hide_and_show_a_level() -> None:
    hidden = JournalFilter().with_level(LogLevelEnum.INFO, shown=False)

    assert _messages(hidden.visible(ENTRIES)) == ["debug detail", "Save failed"]
    assert _messages(hidden.with_level(LogLevelEnum.INFO, shown=True).visible(ENTRIES)) == _messages(
        JournalFilter().visible(ENTRIES)
    )


def test_search_is_accent_insensitive_and_covers_the_source() -> None:
    assert _messages(JournalFilter().with_search("etat").visible(ENTRIES)) == ["État du minuteur"]
    assert len(JournalFilter().with_search("concentrator.test").visible(ENTRIES)) == len(ENTRIES)


def test_clear_view_hides_the_entries_received_so_far() -> None:
    cleared = JournalFilter().cleared(ENTRIES[1].sequence)

    assert _messages(cleared.visible(ENTRIES)) == ["Save failed", "timer started"]
    assert cleared.cleared(0).cleared_through == ENTRIES[1].sequence


def test_pause_freezes_the_view_and_counts_the_hidden_matching_entries() -> None:
    paused = JournalFilter().with_level(LogLevelEnum.DEBUG, shown=False).paused(ENTRIES[0].sequence)

    assert paused.is_paused
    assert _messages(paused.visible(ENTRIES)) == ["État du minuteur"]
    assert paused.hidden_by_pause(ENTRIES) == 2
    assert paused.paused(ENTRIES[-1].sequence) is paused
    assert paused.resumed().hidden_by_pause(ENTRIES) == 0
    assert len(paused.resumed().visible(ENTRIES)) == 3


def test_follow_flag_is_changed_alone() -> None:
    journal_filter = JournalFilter().with_search("timer")

    unfollowed = journal_filter.with_follow(False)

    assert not unfollowed.follow
    assert unfollowed.search == journal_filter.search


def test_level_counts_ignore_the_level_toggles_but_follow_search_and_clear() -> None:
    journal_filter = JournalFilter().with_level(LogLevelEnum.ERROR, shown=False).cleared(ENTRIES[0].sequence)

    counts = journal_filter.level_counts(ENTRIES)

    assert counts[LogLevelEnum.ERROR] == 1
    assert counts[LogLevelEnum.INFO] == 1
    assert counts[LogLevelEnum.DEBUG] == 1
    assert counts[LogLevelEnum.WARNING] == 0
