"""Shared pytest configuration.

Qt reads ``QT_QPA_PLATFORM`` when the ``QApplication`` is created: tests never open a real window.
"""

import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"
