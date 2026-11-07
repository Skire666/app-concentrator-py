"""Native dialog confinement on the real Windows platform, run in a child process (no window shown).

Usage: ``python -m tests.integration.qt.native_dialog_process``. Writes the host and dialog rectangles
(``x y width height``) after the dialog was moved far outside, one per line.
"""

import os
import sys

os.environ["QT_QPA_PLATFORM"] = "windows"

from PySide6.QtWidgets import QApplication, QDialog, QWidget

from concentrator.ui.support.position_clamp_filter import PositionClampFilter
from concentrator.ui.support.window_rects import NativeWindowRects


def main() -> int:
    app = QApplication(sys.argv[:1])
    host = QWidget()
    host.resize(800, 600)
    dialog = QDialog()
    dialog.resize(300, 200)
    rects = NativeWindowRects()
    native = PositionClampFilter(rects, host)
    app.installNativeEventFilter(native)
    rects.move_frame(host, 200, 150)
    native.track(dialog)
    rects.move_frame(dialog, -5000, 5000)
    for box in (rects.frame(host), rects.frame(dialog)):
        sys.stdout.write(f"{box.x} {box.y} {box.width} {box.height}\n")
    native.untrack(dialog)
    rects.move_frame(dialog, -5000, 5000)
    box = rects.frame(dialog)
    sys.stdout.write(f"{box.x} {box.y} {box.width} {box.height}\n")
    app.removeNativeEventFilter(native)
    return 0


if __name__ == "__main__":
    sys.exit(main())
