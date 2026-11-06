"""Build ``dist/Concentrator/Concentrator.exe`` with PyInstaller and validate it with the self-check.

Usage: ``uv run python scripts/build.py``. Steps: PyInstaller (onedir, windowed, no UPX, spec file in
``build/``), copy ``concentrator.ini`` next to the exe (editable without rebuilding), run the exe with
``CONCENTRATOR_SELF_CHECK=1`` and fail if it fails.

PyInstaller runs as ``python -m PyInstaller`` in a subprocess: it ships no type information, so the
in-process ``PyInstaller.__main__.run`` would need type-checker suppressions.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
APP_NAME: Final = "Concentrator"
ENTRY_SCRIPT: Final = REPO_ROOT / "concentrator" / "__main__.py"
ASSETS_DIR: Final = REPO_ROOT / "assets"
ICON_FILE: Final = ASSETS_DIR / "icons" / "concentrator.ico"
INI_FILE: Final = ASSETS_DIR / "config" / "concentrator.ini"
BUNDLED_ASSET_DIRS: Final = ("i18n", "icons")
BUILD_DIR: Final = REPO_ROOT / "build"
DIST_DIR: Final = REPO_ROOT / "dist"
APP_DIR: Final = DIST_DIR / APP_NAME
EXE_FILE: Final = APP_DIR / f"{APP_NAME}.exe"
SELF_CHECK_VARIABLE: Final = "CONCENTRATOR_SELF_CHECK"
SELF_CHECK_TIMEOUT_S: Final = 120


def pyinstaller_command() -> list[str]:
    """Build the PyInstaller command line; every path is absolute (``--specpath`` moves the base).

    Returns:
        The command.
    """
    command = [sys.executable, "-m", "PyInstaller", str(ENTRY_SCRIPT), "--name", APP_NAME]
    command += ["--onedir", "--windowed", "--noupx", "--noconfirm", "--clean"]
    command += ["--icon", str(ICON_FILE), "--specpath", str(BUILD_DIR), "--workpath", str(BUILD_DIR / "work")]
    command += ["--distpath", str(DIST_DIR), "--copy-metadata", "concentrator"]
    for name in BUNDLED_ASSET_DIRS:
        command += ["--add-data", f"{ASSETS_DIR / name}{os.pathsep}assets/{name}"]
    return command


def self_check(exe: Path) -> int:
    """Run the frozen application in self-check mode.

    Args:
        exe: Built executable.

    Returns:
        Its exit code (0 = every check passed).
    """
    environment = {**os.environ, SELF_CHECK_VARIABLE: "1"}
    try:
        completed = subprocess.run([str(exe)], env=environment, check=False, timeout=SELF_CHECK_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        print(f"Self-check timed out after {SELF_CHECK_TIMEOUT_S} s")
        return 1
    return completed.returncode


def main() -> int:
    """Build, copy the ini, self-check.

    Returns:
        0 on success, 1 on failure.
    """
    if not ICON_FILE.is_file():
        print(f"Application icon missing: {ICON_FILE}")
        return 1
    print("=== PyInstaller", flush=True)
    if subprocess.run(pyinstaller_command(), cwd=REPO_ROOT, check=False).returncode != 0:
        print("PyInstaller failed")
        return 1
    shutil.copy2(INI_FILE, APP_DIR / INI_FILE.name)
    print(f"=== Copied {INI_FILE.name} next to {EXE_FILE.name}")
    exit_code = self_check(EXE_FILE)
    if exit_code != 0:
        print(f"=== Self-check FAILED (exit code {exit_code}); see the log in %LOCALAPPDATA%\\Concentrator\\logs")
        return 1
    print(f"=== Self-check passed: {EXE_FILE}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
