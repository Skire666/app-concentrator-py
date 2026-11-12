"""Keyboard mnemonics of field captions and buttons (``&`` before the letter in the catalogs, phase 8).

A caption ``QLabel`` gets its field as buddy: Alt and the letter move the focus to the field, and the field
takes the caption, without ``&``, as its accessible name.
"""

import re
from typing import Final, cast

from PySide6.QtWidgets import QLabel, QWidget

_MARKER: Final = re.compile(r"&(.)")


def mnemonic_free(text: str) -> str:
    """Remove the mnemonic markers as Qt shows the text ("&&" stays one "&").

    Args:
        text: Catalog text such as ``"&Duration"``.

    Returns:
        The text read by screen readers (``"Duration"``).
    """
    return _MARKER.sub(r"\1", text)


def accessible_name(text: str, fallback: str = "") -> str:
    """Name a control for screen readers from its snapshot.

    Args:
        text: Label of the control, possibly with a mnemonic marker.
        fallback: Used when the control shows no text (icon-only buttons): usually its tooltip.

    Returns:
        The name.
    """
    return mnemonic_free(text) or fallback


def bind_caption(caption: QLabel, field: QWidget) -> None:
    """Make a caption label the label of its field (focus on Alt and the letter).

    Args:
        caption: Caption shown before the field.
        field: Field (a composite widget forwards the focus to its first input through its focus proxy).
    """
    caption.setBuddy(field)


def set_caption(caption: QLabel, text: str) -> None:
    """Show a caption and name its buddy field after it for screen readers.

    Args:
        caption: Caption bound with ``bind_caption`` (or without buddy).
        text: Translated caption, possibly with a mnemonic marker.
    """
    caption.setText(text)
    buddy = cast("QWidget | None", caption.buddy())  # None without buddy, although the stubs say QWidget
    if buddy is None:
        return
    name = mnemonic_free(text)
    buddy.setAccessibleName(name)
    proxy = buddy.focusProxy()
    if proxy is not None:
        proxy.setAccessibleName(name)
