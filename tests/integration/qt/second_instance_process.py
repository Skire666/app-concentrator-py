"""A second launch, run in a child process by ``test_qt_single_instance_guard``.

Usage: ``python -m tests.integration.qt.second_instance_process <lock_dir> <key>``. Writes
``<acquired> <codes or success>`` on stdout.
"""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication

from concentrator.infrastructure.qt.qt_single_instance_guard import QtSingleInstanceGuard


def main() -> int:
    lock_dir, key = Path(sys.argv[1]), sys.argv[2]
    app = QCoreApplication(sys.argv[:1])
    guard = QtSingleInstanceGuard(lock_dir=lock_dir, key=key, timeout_ms=5000, parent=app)
    result = guard.acquire()
    codes = ",".join(code.name for code in result.validation.error_codes) or "success"
    sys.stdout.write(f"{result.data} {codes}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
