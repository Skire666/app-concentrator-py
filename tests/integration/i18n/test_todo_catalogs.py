"""Task rows and tabs rendered with the real catalogs, in both languages."""

from dataclasses import replace
from datetime import UTC, date, datetime, time

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.todo.recurrence import Recurrence
from concentrator.domain.todo.recurrence_end_enum import RecurrenceEndEnum
from concentrator.domain.todo.recurrence_frequency_enum import RecurrenceFrequencyEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.domain.todo.weekday_enum import WeekdayEnum
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from tests.fakes.fake_clock import FakeClock
from tests.fakes.todo_factory import make_task
from tests.fakes.todo_stack import LINKS

LANGUAGES = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def _translator(language: LanguageEnum) -> JsonCatalogTranslator:
    catalogs = load_catalogs(AppPaths.from_runtime().i18n_dir, LANGUAGES, LanguageEnum.ENGLISH)
    return JsonCatalogTranslator(catalogs.value_or({}), language=language, fallback_language=LanguageEnum.ENGLISH)


def _formatter(language: LanguageEnum) -> TaskRowFormatter:
    translator = _translator(language)
    return TaskRowFormatter(translator, DateTimeFormatter(translator, FakeClock(NOW)), LINKS)


@pytest.mark.parametrize(
    ("language", "columns", "due", "title", "created"),
    [
        (
            LanguageEnum.ENGLISH,
            ("Done", "Task", "List", "Due", "Repeat", "Times", "Links", "Created", "Updated"),
            "2026-11-09 08:05",
            "Report (+1 line)",
            "2026-11-06 17:41",
        ),
        (
            LanguageEnum.FRENCH,
            ("Faite", "Tâche", "Liste", "Échéance", "Répétition", "Fois", "Liens", "Créée", "Modifiée"),
            "09/11/2026 08:05",
            "Report (+1 ligne)",
            "06/11/2026 17:41",
        ),
    ],
)
def test_rows_are_formatted_in_each_language(
    language: LanguageEnum, columns: tuple[str, ...], due: str, title: str, created: str
) -> None:
    formatter = _formatter(language)
    task = make_task(1, text="Report\nsources", due_date=date(2026, 11, 9), due_time=time(8, 5))

    row = formatter.row(task, FakeClock(NOW).now_local())

    assert formatter.columns() == columns
    assert (row.cells[1], row.cells[3], row.cells[7]) == (title, due, created)


@pytest.mark.parametrize(
    ("language", "archived", "plural"),
    [(LanguageEnum.ENGLISH, "Archived", "(+2 lines)"), (LanguageEnum.FRENCH, "Archivée", "(+2 lignes)")],
)
def test_state_and_plural_texts_exist_in_each_language(language: LanguageEnum, archived: str, plural: str) -> None:
    formatter = _formatter(language)

    row = formatter.row(make_task(1, text="a\nb\nc", state=TaskStateEnum.ARCHIVED), FakeClock(NOW).now_local())

    assert row.cells[0] == archived
    assert row.cells[1] == "a " + plural


def _weekly(end_kind: RecurrenceEndEnum, **ends: int) -> Recurrence:
    return Recurrence.create(
        frequency=RecurrenceFrequencyEnum.WEEKLY,
        interval=2,
        weekdays=(WeekdayEnum.MONDAY, WeekdayEnum.FRIDAY),
        anchor_date=date(2026, 11, 6),
        end_kind=end_kind,
        end_date=date(2026, 12, 31) if end_kind is RecurrenceEndEnum.ON_DATE else None,
        end_count=ends.get("count"),
    )


@pytest.mark.parametrize(
    ("language", "times", "until", "monthly", "yearly", "short"),
    [
        (
            LanguageEnum.ENGLISH,
            "Every 2 weeks on Monday and Friday, 10 times",
            "Every 2 weeks on Monday and Friday, until 2026-12-31",
            "Every month on day 31",
            "Every year on 02-29",
            "Every day",
        ),
        (
            LanguageEnum.FRENCH,
            "Toutes les 2 semaines, le lundi et vendredi, 10 fois",
            "Toutes les 2 semaines, le lundi et vendredi, jusqu'au 31/12/2026",
            "Tous les mois, le 31",
            "Tous les ans, le 29/02",
            "Tous les jours",
        ),
    ],
)
def test_recurrence_summaries_in_each_language(
    language: LanguageEnum, times: str, until: str, monthly: str, yearly: str, short: str
) -> None:
    summaries = _formatter(language).summaries

    def other(frequency: RecurrenceFrequencyEnum, anchor: date) -> Recurrence:
        return Recurrence.create(frequency=frequency, interval=1, anchor_date=anchor, end_kind=RecurrenceEndEnum.NEVER)

    assert summaries.full(_weekly(RecurrenceEndEnum.AFTER_COUNT, count=10)) == times
    assert summaries.full(_weekly(RecurrenceEndEnum.ON_DATE)) == until
    assert summaries.full(other(RecurrenceFrequencyEnum.MONTHLY, date(2026, 10, 31))) == monthly
    assert summaries.full(other(RecurrenceFrequencyEnum.YEARLY, date(2028, 2, 29))) == yearly
    assert summaries.short(other(RecurrenceFrequencyEnum.DAILY, date(2026, 10, 31))) == short


@pytest.mark.parametrize(
    ("language", "days"),
    [(LanguageEnum.ENGLISH, "Monday, Wednesday and Friday"), (LanguageEnum.FRENCH, "lundi, mercredi et vendredi")],
)
def test_weekday_lists_in_each_language(language: LanguageEnum, days: str) -> None:
    summaries = _formatter(language).summaries

    assert summaries.day_list((WeekdayEnum.MONDAY, WeekdayEnum.WEDNESDAY, WeekdayEnum.FRIDAY)) == days
    assert summaries.day_list((WeekdayEnum.SUNDAY,)) in {"Sunday", "dimanche"}


@pytest.mark.parametrize(
    ("language", "repeat", "counter"),
    [
        (LanguageEnum.ENGLISH, "Every 2 weeks", "12 of 87 tasks"),
        (LanguageEnum.FRENCH, "Toutes les 2 semaines", "12 sur 87 tâches"),
    ],
)
def test_new_columns_and_counter_in_each_language(language: LanguageEnum, repeat: str, counter: str) -> None:
    task = replace(
        make_task(1, text="Backup\nD:/Projects\nhttps://example.org", due_date=date(2026, 11, 9)),
        recurrence=_weekly(RecurrenceEndEnum.AFTER_COUNT, count=10),
        occurrences_done=3,
    )

    row = _formatter(language).row(task, FakeClock(NOW).now_local(), "Work")

    assert row.cells[2:7] == ("Work", row.cells[3], repeat, "3 / 10", "2")
    assert _translator(language).tr_plural("todo.filter.counter", 87, shown=12) == counter
