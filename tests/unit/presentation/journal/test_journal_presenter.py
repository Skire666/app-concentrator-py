import logging

import pytest

from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.log_level_enum import LogLevelEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.layout_keys import LAYOUT_JOURNAL_FOLLOW, LAYOUT_JOURNAL_LEVELS
from concentrator.presentation.common.row_tone_enum import RowToneEnum
from concentrator.presentation.shell.shell_page_enum import ShellPageEnum
from tests.fakes.fake_log_feed import FakeLogFeed
from tests.fakes.journal_stack import COOLDOWN_MS, DEBOUNCE_MS, LOG_DIR, JournalStack


@pytest.fixture
def stack() -> JournalStack:
    return JournalStack()


def _click(stack: JournalStack, action: ActionIdEnum) -> None:
    stack.presenter.on_action_requested(int(action))
    stack.settle()


def test_hidden_page_never_reads_the_records(stack: JournalStack) -> None:
    stack.feed.log_many(3)

    for _ in range(5):
        stack.tick()

    assert stack.feed.reads == 0
    assert stack.journal == []


def test_showing_the_page_reads_and_renders_the_startup_entries(stack: JournalStack) -> None:
    stack.feed.log("Concentrator starting", logging.INFO, source="concentrator.bootstrap.app")

    stack.show()

    row = stack.last.table.rows[0]
    assert row.cells == (
        "en:format.time_with_milliseconds(hour=10,minute=00,second=01,millisecond=250)",
        "en:journal.level.info",
        "concentrator.bootstrap.app",
        "MainThread",
        "Concentrator starting",
    )
    assert row.tone is RowToneEnum.NORMAL
    assert stack.last.table.columns[0] == "en:journal.column.time"
    assert stack.last.table.scroll_to_end


def test_visible_page_polls_and_renders_only_when_something_changed(stack: JournalStack) -> None:
    stack.show()
    renders = len(stack.journal)

    stack.tick()
    stack.tick()
    assert len(stack.journal) == renders

    stack.feed.log("new")
    stack.tick()
    assert len(stack.journal) == renders + 1
    assert stack.messages() == ["new"]


def test_leaving_the_page_stops_polling(stack: JournalStack) -> None:
    stack.show()
    stack.show(ShellPageEnum.FOCUS)
    reads = stack.feed.reads

    stack.tick()

    assert stack.feed.reads == reads


def test_errors_logged_while_hidden_show_a_badge_cleared_on_showing(stack: JournalStack) -> None:
    stack.feed.log("old failure", logging.ERROR)
    stack.tick()
    assert stack.presenter.badge_count() == 1

    stack.feed.log("warning", logging.WARNING)
    stack.feed.log("crash", logging.CRITICAL)
    stack.tick()
    assert stack.presenter.badge_count() == 2
    assert stack.shell == [1, 2]

    stack.show()
    assert stack.presenter.badge_count() == 0
    assert stack.shell[-1] == 0

    stack.feed.log("seen while shown", logging.ERROR)
    stack.tick()
    stack.show(ShellPageEnum.FOCUS)
    stack.tick()
    assert stack.presenter.badge_count() == 0


def test_errors_logged_at_startup_count_until_the_journal_is_shown() -> None:
    feed = FakeLogFeed()
    feed.log("startup failure", logging.ERROR)
    stack = JournalStack(feed=feed)

    stack.tick()
    assert stack.presenter.badge_count() == 1

    stack.show()
    assert stack.presenter.badge_count() == 0


def test_level_toggle_hides_a_level_and_is_remembered(stack: JournalStack) -> None:
    stack.feed.log("info")
    stack.feed.log("debug", logging.DEBUG)
    stack.show()

    stack.presenter.on_level_toggled(int(LogLevelEnum.DEBUG))
    stack.settle()

    assert stack.messages() == ["info"]
    toggles = {toggle.level: toggle for toggle in stack.last.toolbar.levels}
    assert not toggles[int(LogLevelEnum.DEBUG)].checked
    assert toggles[int(LogLevelEnum.DEBUG)].text == "en:journal.level.count(level=en:journal.level.debug,count=1)"
    assert stack.preferences.values[LAYOUT_JOURNAL_LEVELS] == "2,3,4,5"
    assert JournalStack(preferences=stack.preferences.values).presenter.build_snapshot().toolbar.levels[0].checked is (
        False
    )


def test_level_toggles_are_disabled_during_the_cooldown(stack: JournalStack) -> None:
    stack.show()

    stack.presenter.on_level_toggled(int(LogLevelEnum.INFO))
    stack.scheduler.run_pending()

    assert not any(toggle.enabled for toggle in stack.last.toolbar.levels)
    stack.presenter.on_level_toggled(int(LogLevelEnum.INFO))
    stack.scheduler.advance(COOLDOWN_MS)
    assert all(toggle.enabled for toggle in stack.last.toolbar.levels)
    assert not stack.last.toolbar.levels[1].checked


def test_unknown_level_is_ignored(stack: JournalStack) -> None:
    stack.show()

    stack.presenter.on_level_toggled(99)
    stack.settle()

    assert all(toggle.checked for toggle in stack.last.toolbar.levels)


def test_search_applies_after_the_debounce_and_keeps_the_typed_text(stack: JournalStack) -> None:
    stack.feed.log("État sauvegardé")
    stack.feed.log("timer started")
    stack.show()

    stack.presenter.on_search_changed("e")
    stack.presenter.on_search_changed("et")
    stack.presenter.on_search_changed("etat")
    stack.scheduler.advance(DEBOUNCE_MS - 1)
    assert len(stack.messages()) == 2

    stack.scheduler.advance(1)
    assert stack.messages() == ["État sauvegardé"]
    assert stack.last.toolbar.search.text == "etat"


def test_search_typed_during_the_cooldown_is_applied_later(stack: JournalStack) -> None:
    stack.feed.log("alpha")
    stack.feed.log("beta")
    stack.show()
    stack.presenter.on_search_changed("alpha")
    stack.scheduler.advance(DEBOUNCE_MS)

    stack.settle()
    busy = stack.gate.begin(ActionIdEnum.JOURNAL_SEARCH).data
    assert busy is not None
    stack.presenter.on_search_changed("beta")
    stack.scheduler.advance(DEBOUNCE_MS)
    assert stack.messages() == ["alpha"]

    busy.finish()
    stack.settle()
    assert stack.messages() == ["beta"]


def test_pause_freezes_the_rows_and_counts_the_new_entries(stack: JournalStack) -> None:
    stack.feed.log("before")
    stack.show()

    _click(stack, ActionIdEnum.JOURNAL_TOGGLE_PAUSE)
    stack.feed.log("during 1")
    stack.feed.log("during 2")
    stack.tick()

    assert stack.messages() == ["before"]
    assert stack.last.toolbar.pause.checked
    assert stack.last.toolbar.paused_caption == "en:journal.paused.other(count=2)"
    assert not stack.last.table.scroll_to_end

    _click(stack, ActionIdEnum.JOURNAL_TOGGLE_PAUSE)
    assert stack.messages() == ["before", "during 1", "during 2"]
    assert not stack.last.toolbar.paused_caption


def test_follow_is_toggled_and_remembered(stack: JournalStack) -> None:
    stack.show()

    _click(stack, ActionIdEnum.JOURNAL_TOGGLE_FOLLOW)

    assert not stack.last.toolbar.follow.checked
    assert not stack.last.table.scroll_to_end
    assert stack.preferences.values[LAYOUT_JOURNAL_FOLLOW] == "0"


def test_clear_view_hides_what_was_received(stack: JournalStack) -> None:
    stack.feed.log_many(3)
    stack.show()

    _click(stack, ActionIdEnum.JOURNAL_CLEAR_VIEW)
    assert stack.messages() == []
    assert stack.last.table.empty_text == "en:journal.empty"

    stack.feed.log("after")
    stack.tick()
    assert stack.messages() == ["after"]


def test_selection_shows_the_current_entry_in_full_and_copy_takes_the_selection(stack: JournalStack) -> None:
    stack.feed.log("first")
    stack.feed.log("Traceback line 1\nline 2", logging.ERROR, thread="writer")
    stack.show()
    assert not stack.last.toolbar.copy.enabled

    stack.presenter.on_selection_changed((0, 1), 1)
    stack.scheduler.run_pending()

    assert stack.last.table.selection == (0, 1)
    assert stack.last.detail.text == (
        "2026-11-06 10:00:02.250 | ERROR    | writer | concentrator.test | Traceback line 1\nline 2"
    )
    assert stack.last.table.rows[1].cells[4] == "en:journal.message.more_lines(text=Traceback line 1)"
    assert stack.last.table.rows[1].tone is RowToneEnum.ERROR
    _click(stack, ActionIdEnum.JOURNAL_COPY)
    assert stack.clipboard.texts == [
        (
            "2026-11-06 10:00:01.250 | INFO     | MainThread | concentrator.test | first\n"
            "2026-11-06 10:00:02.250 | ERROR    | writer | concentrator.test | Traceback line 1\nline 2"
        )
    ]


def test_copy_keeps_the_newest_selected_rows_up_to_the_limit() -> None:
    stack = JournalStack(copy_max_rows=2)
    stack.feed.log_many(3)
    stack.show()
    stack.presenter.on_selection_changed((0, 1, 2), 0)

    _click(stack, ActionIdEnum.JOURNAL_COPY)

    assert [line.rsplit("| ", 1)[1] for line in stack.clipboard.texts[0].split("\n")] == ["message 1", "message 2"]


def test_copy_without_selection_does_nothing(stack: JournalStack) -> None:
    stack.show()
    stack.presenter.on_selection_changed((5,), 7)

    _click(stack, ActionIdEnum.JOURNAL_COPY)

    assert stack.clipboard.texts == []
    assert not stack.last.detail.text
    assert stack.last.detail.placeholder == "en:journal.detail.placeholder"


def test_open_log_folder_creates_a_missing_folder(stack: JournalStack) -> None:
    stack.show()

    _click(stack, ActionIdEnum.JOURNAL_OPEN_LOG_FOLDER)

    assert stack.opener.opened == [(LOG_DIR, True)]


def test_refused_folder_is_logged(stack: JournalStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.opener.result = ValidationResult.failure(ErrorCodeEnum.LINK_OPEN_FAILED)

    _click(stack, ActionIdEnum.JOURNAL_OPEN_LOG_FOLDER)

    assert "LINK_OPEN_FAILED" in caplog.text


def test_unknown_action_is_logged(stack: JournalStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.presenter.on_action_requested(int(ActionIdEnum.TIMER_START))

    assert "not handled" in caplog.text


def test_full_buffer_drops_the_oldest_rows_and_keeps_the_other_row_objects() -> None:
    stack = JournalStack(capacity=3)
    stack.feed.log_many(3)
    stack.show()
    kept = stack.last.table.rows[1:]

    stack.feed.log("newest")
    stack.tick()

    assert stack.messages() == ["message 1", "message 2", "newest"]
    assert all(new is old for new, old in zip(stack.last.table.rows, kept, strict=False))


def test_fifty_entries_per_tick_are_appended_in_one_render(stack: JournalStack) -> None:
    stack.show()
    renders = len(stack.journal)

    stack.feed.log_many(50)
    stack.tick()

    assert len(stack.journal) == renders + 1
    assert len(stack.last.table.rows) == 50


def test_language_change_rebuilds_the_rows(stack: JournalStack) -> None:
    stack.feed.log("x")
    stack.show()

    stack.translator.set_language(LanguageEnum.FRENCH)
    stack.renderer.request_all()
    stack.scheduler.run_pending()

    assert stack.last.table.rows[0].cells[1] == "fr:journal.level.info"


def test_reset_layout_shows_every_level_and_follows_again(stack: JournalStack) -> None:
    stack.show()
    stack.presenter.on_level_toggled(int(LogLevelEnum.INFO))
    stack.settle()
    _click(stack, ActionIdEnum.JOURNAL_TOGGLE_FOLLOW)

    stack.presenter.reset_layout()
    stack.scheduler.run_pending()

    assert all(toggle.checked for toggle in stack.last.toolbar.levels)
    assert stack.last.toolbar.follow.checked


@pytest.mark.parametrize("stored", ["1,x", "1,9", "-1"])
def test_stored_levels_not_understood_take_the_default(stored: str, caplog: pytest.LogCaptureFixture) -> None:
    stack = JournalStack(preferences={LAYOUT_JOURNAL_LEVELS: stored, LAYOUT_JOURNAL_FOLLOW: "0"})

    snapshot = stack.presenter.build_snapshot()

    assert all(toggle.checked for toggle in snapshot.toolbar.levels)
    assert not snapshot.toolbar.follow.checked
    assert "ignored" in caplog.text


def test_every_level_may_be_stored_hidden() -> None:
    stack = JournalStack(preferences={LAYOUT_JOURNAL_LEVELS: ""})

    assert not any(toggle.checked for toggle in stack.presenter.build_snapshot().toolbar.levels)


def test_ticks_and_renders_write_nothing_to_the_log(stack: JournalStack, caplog: pytest.LogCaptureFixture) -> None:
    stack.show()

    with caplog.at_level(logging.DEBUG):
        for index in range(20):
            stack.feed.log(f"record {index}", logging.DEBUG)
            stack.tick()
            stack.presenter.on_selection_changed((0,), 0)
            stack.scheduler.run_pending()
        stack.show(ShellPageEnum.FOCUS)
        stack.feed.log("error", logging.ERROR)
        stack.tick()

    assert [record.getMessage() for record in caplog.records if record.name.startswith("concentrator")] == []
