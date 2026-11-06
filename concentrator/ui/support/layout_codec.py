"""Qt layout blobs <-> opaque base64 strings stored through ``LayoutStateKeeper`` (ADR-022)."""

import base64
import binascii

from PySide6.QtCore import QByteArray


def encode_blob(blob: QByteArray) -> str:
    """Encode a ``saveGeometry`` / ``saveState`` blob.

    Args:
        blob: Qt state bytes.

    Returns:
        Base64 text.
    """
    return base64.b64encode(blob.data()).decode("ascii")


def decode_blob(text: str) -> QByteArray | None:
    """Decode a stored blob.

    Args:
        text: Base64 text read from ``ui-state.ini``.

    Returns:
        The bytes, or ``None`` when the text is not valid base64 (the caller falls back to defaults).
    """
    try:
        return QByteArray(base64.b64decode(text, validate=True))
    except binascii.Error, ValueError:
        return None
