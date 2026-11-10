import pytest

from concentrator.presentation.common.text_search import TextSearch, fold


@pytest.mark.parametrize(
    ("text", "expected"),
    [("État", "etat"), ("Ça GÉNÈRE", "ca genere"), ("ﬁchier", "fichier"), ("Straße", "strasse"), ("", "")],
)
def test_fold_removes_accents_and_case(text: str, expected: str) -> None:
    assert fold(text) == expected


def test_accent_insensitive_search_finds_the_accented_text() -> None:
    assert TextSearch.parse("etat").matches(fold("État du minuteur"))
    assert TextSearch.parse("ÉTAT").matches(fold("etat"))


def test_every_word_is_required_in_any_order() -> None:
    search = TextSearch.parse("  timer   saved ")

    assert search.terms == ("timer", "saved")
    assert search.matches(fold("Saved the timer"))
    assert not search.matches(fold("timer started"))


def test_blank_query_matches_everything() -> None:
    search = TextSearch.parse("   ")

    assert search.is_empty
    assert search.query == "   "
    assert search.matches("")
    assert TextSearch().is_empty
