"""Task rows and tabs rendered with the real catalogs, in both languages."""

from datetime import UTC, date, datetime, time

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.todo.task_state_enum import TaskStateEnum
from concentrator.infrastructure.i18n.json_catalog_translator import JsonCatalogTranslator, load_catalogs
from concentrator.infrastructure.system.app_paths import AppPaths
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.todo.task_row_formatter import TaskRowFormatter
from tests.fakes.fake_clock import FakeClock
from tests.fakes.todo_factory import make_task

LANGUAGES = (LanguageEnum.ENGLISH, LanguageEnum.FRENCH)
NOW = datetime(2026, 11, 10, 9, 0, tzinfo=UTC)


def _translator(language: LanguageEnum) -> JsonCatalogTranslator:
    catalogs = load_catalogs(AppPaths.from_runtime().i18n_dir, LANGUAGES, LanguageEnum.ENGLISH)
    return JsonCatalogTranslator(catalogs.value_or({}), language=language, fallback_language=LanguageEnum.ENGLISH)


def _formatter(language: LanguageEnum) -> TaskRowFormatter:
    translator = _translator(language)
    return TaskRowFormatter(translator, DateTimeFormatter(translator, FakeClock(NOW)))


@pytest.mark.parametrize(
    ("language", "columns", "due", "title", "created"),
    [
        (
            LanguageEnum.ENGLISH,
            ("Done", "Task", "Due", "Created", "Updated"),
            "2026-11-09 08:05",
            "Report (+1 line)",
            "2026-11-06 17:41",
        ),
        (
            LanguageEnum.FRENCH,
            ("Faite", "Tâche", "Échéance", "Créée", "Modifiée"),
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
    assert row.cells[1:4] == (title, due, created)


@pytest.mark.parametrize(
    ("language", "archived", "plural"),
    [(LanguageEnum.ENGLISH, "Archived", "(+2 lines)"), (LanguageEnum.FRENCH, "Archivée", "(+2 lignes)")],
)
def test_state_and_plural_texts_exist_in_each_language(language: LanguageEnum, archived: str, plural: str) -> None:
    formatter = _formatter(language)

    row = formatter.row(make_task(1, text="a\nb\nc", state=TaskStateEnum.ARCHIVED), FakeClock(NOW).now_local())

    assert row.cells[0] == archived
    assert row.cells[1] == "a " + plural
