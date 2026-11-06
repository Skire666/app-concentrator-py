"""A second launch of the whole application, run in a child process by ``test_two_stage_logging``.

Usage: ``python -m tests.integration.bootstrap.second_launch_process <app_dir> <assets_dir> <appdata>
<localappdata>``. Exits with the code returned by ``bootstrap.app.run``.
"""

import os
import sys
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from concentrator.bootstrap.app import run
from concentrator.infrastructure.system.app_paths import AppPaths


def main() -> int:
    app_dir, assets_dir, appdata, localappdata = (Path(argument) for argument in sys.argv[1:5])
    environment = {"APPDATA": str(appdata), "LOCALAPPDATA": str(localappdata)}
    return run(AppPaths(app_dir, assets_dir, app_dir / "concentrator.ini", environment), self_check=False)


if __name__ == "__main__":
    sys.exit(main())
