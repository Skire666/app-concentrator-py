"""Entry point: ``python -m concentrator``, the ``concentrator`` gui-script and the PyInstaller script."""

import sys

from concentrator.bootstrap.app import main as run_application


def main() -> int:
    """Start Concentrator.

    Returns:
        The process exit code.
    """
    return run_application()


if __name__ == "__main__":
    sys.exit(main())
