"""Keyboard mnemonics of the catalogs (phase 8): one per text, unique per window, in both languages.

A window lists the texts shown at the same time with a mnemonic: the captions and buttons of a dialog, or
the module bar with the settings page. Alt and a letter must reach a single control (Qt ignores case).
"""

import json
import re
from typing import Final, cast

import pytest

from tests.architecture.source_tree import REPO_ROOT

CATALOG_DIR: Final = REPO_ROOT / "assets" / "i18n"
LANGUAGES: Final = ("en", "fr")
MARKER: Final = re.compile(r"&(.)")
DIALOG_BUTTONS: Final = ("cancel", "save")
WINDOWS: Final = {
    "timer dialog": (
        "timer.edit.duration",
        "timer.edit.sound",
        "timer.edit.volume",
        "timer.edit.plays",
        "timer.edit.loop_forever",
        "timer.edit.auto_stop",
        "timer.edit.auto_restart",
        *(f"action.timer_edit_{button}" for button in DIALOG_BUTTONS),
    ),
    "favorite dialog": (
        "preset.edit.label",
        "preset.edit.duration",
        *(f"action.preset_edit_{button}" for button in DIALOG_BUTTONS),
    ),
    "hourly chime dialog": (
        "chime.edit.sound",
        "chime.edit.volume",
        "chime.edit.start_hour",
        "chime.edit.end_hour",
        *(f"action.chime_edit_{button}" for button in DIALOG_BUTTONS),
    ),
    "list dialog": (
        "todo.list_edit.name",
        "todo.list_edit.description",
        "todo.list_edit.priority",
        *(f"action.list_edit_{button}" for button in DIALOG_BUTTONS),
    ),
    "task dialog": (
        "todo.task_edit.text",
        "todo.task_edit.list",
        "todo.task_edit.due_date",
        "todo.task_edit.due_time",
        "todo.task_edit.repeat",
        "todo.task_edit.repeat_every",
        "todo.task_edit.repeat_ends",
        *(f"action.task_edit_{button}" for button in DIALOG_BUTTONS),
    ),
    "settings page": (
        "action.shell_show_focus",
        "action.shell_show_journal",
        "action.shell_show_settings",
        "settings.language",
        "settings.log_level",
        "settings.notify_when_inactive",
        "settings.chime.enabled",
        "chime.edit.sound",
        "chime.edit.volume",
        "chime.edit.start_hour",
        "chime.edit.end_hour",
        "action.settings_revert",
        "action.settings_save",
    ),
}


def _catalog(language: str) -> dict[str, str]:
    return cast("dict[str, str]", json.loads((CATALOG_DIR / f"{language}.json").read_text(encoding="utf-8")))


def _letters(text: str) -> list[str]:
    """Mnemonic letters of a text, lower case ("&&" is a literal ampersand, not a marker)."""
    return [match.group(1).lower() for match in MARKER.finditer(text) if match.group(1) != "&"]


@pytest.mark.parametrize("language", LANGUAGES)
def test_a_text_has_at_most_one_mnemonic_on_an_ascii_letter(language: str) -> None:
    wrong = {
        key: text
        for key, text in _catalog(language).items()
        if len(_letters(text)) > 1 or any(not (letter.isascii() and letter.isalpha()) for letter in _letters(text))
    }

    assert wrong == {}


@pytest.mark.parametrize("language", LANGUAGES)
@pytest.mark.parametrize("window", sorted(WINDOWS))
def test_every_text_of_a_window_has_its_own_mnemonic(language: str, window: str) -> None:
    catalog = _catalog(language)
    letters = {key: _letters(catalog[key]) for key in WINDOWS[window]}

    missing = sorted(key for key, found in letters.items() if not found)
    used = [found[0] for found in letters.values() if found]
    assert missing == []
    assert sorted(used) == sorted(set(used)), letters


@pytest.mark.parametrize("language", LANGUAGES)
def test_mnemonics_appear_only_in_the_texts_of_the_windows(language: str) -> None:
    listed = {key for keys in WINDOWS.values() for key in keys}

    unexpected = sorted(key for key, text in _catalog(language).items() if _letters(text) and key not in listed)

    assert unexpected == []
