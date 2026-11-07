import pytest

from concentrator.domain.common.multiline_text import MultilineText


@pytest.mark.parametrize("text", ["a\r\nb", "a\nb", "a\rb"])
def test_from_text_splits_on_every_line_break(text: str) -> None:
    assert MultilineText.from_text(text).lines == ("a", "b")


def test_from_text_strips_trailing_whitespace_per_line() -> None:
    assert MultilineText.from_text("  keep leading  \nnext\t ").lines == ("  keep leading", "next")


def test_from_text_trims_blank_edges_but_keeps_inner_blank_lines() -> None:
    text = "\n   \nfirst\n\n  \nlast\n \n"

    assert MultilineText.from_text(text).lines == ("first", "", "", "last")


@pytest.mark.parametrize("text", ["", "   ", "\n\r\n \t \n"])
def test_from_text_blank_input_gives_empty_value(text: str) -> None:
    value = MultilineText.from_text(text)

    assert value.lines == ()
    assert value.is_blank
    assert value.line_count == 0
    assert not value.first_line
    assert not value.as_text()


def test_from_lines_normalizes_lines_with_embedded_breaks() -> None:
    assert MultilineText.from_lines(["", "a\r\nb  ", "c"]).lines == ("a", "b", "c")


def test_as_text_first_line_and_line_count() -> None:
    value = MultilineText.from_text("Title\n\nBody")

    assert value.as_text() == "Title\n\nBody"
    assert value.first_line == "Title"
    assert value.line_count == 3
    assert not value.is_blank


def test_constructor_keeps_lines_as_given() -> None:
    value = MultilineText(("", ""))

    assert value.line_count == 2
    assert value.is_blank


def test_values_with_same_lines_are_equal() -> None:
    assert MultilineText.from_text("a\nb") == MultilineText(("a", "b"))
