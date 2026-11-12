"""Build ``dist/Concentrator/Concentrator.exe`` with PyInstaller and validate it with the self-check.

Usage: ``uv run python scripts/build.py [--release]``. Steps: Windows version resource generated into
``build/`` from the version of ``pyproject.toml``, PyInstaller (onedir, windowed, no UPX, spec file in
``build/``), removal of the Qt and Python parts Concentrator never loads, copy of ``concentrator.ini`` next to the exe
(editable without rebuilding), then the exe runs with ``CONCENTRATOR_SELF_CHECK=1`` and the build fails if it
fails. ``--release`` also zips the folder into ``dist/Concentrator-<version>-win64.zip``.

PyInstaller runs as ``python -m PyInstaller`` in a subprocess: it ships no type information, so the
in-process ``PyInstaller.__main__.run`` would need type-checker suppressions.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path
from typing import Final

REPO_ROOT: Final = Path(__file__).resolve().parents[1]
APP_NAME: Final = "Concentrator"
ENTRY_SCRIPT: Final = REPO_ROOT / "concentrator" / "__main__.py"
ASSETS_DIR: Final = REPO_ROOT / "assets"
ICON_FILE: Final = ASSETS_DIR / "icons" / "concentrator.ico"
INI_FILE: Final = ASSETS_DIR / "config" / "concentrator.ini"
PYPROJECT_FILE: Final = REPO_ROOT / "pyproject.toml"
BUNDLED_ASSET_DIRS: Final = ("i18n", "icons", "sounds")
BUILD_DIR: Final = REPO_ROOT / "build"
DIST_DIR: Final = REPO_ROOT / "dist"
APP_DIR: Final = DIST_DIR / APP_NAME
EXE_FILE: Final = APP_DIR / f"{APP_NAME}.exe"
VERSION_FILE: Final = BUILD_DIR / "version_info.txt"
SELF_CHECK_VARIABLE: Final = "CONCENTRATOR_SELF_CHECK"
SELF_CHECK_TIMEOUT_S: Final = 120
COMPANY_NAME: Final = "skire666"
COPYRIGHT: Final = "Public domain (Unlicense)"
RELEASE_SUFFIX: Final = "win64"
BYTES_PER_MB: Final = 1_000_000
VERSION_PATTERN: Final = re.compile(r"^(\d+)\.(\d+)\.(\d+)")
INTERNAL_DIR: Final = Path("_internal")
QT_DIR: Final = INTERNAL_DIR / "PySide6"
TRIMMED_PYTHON_PARTS: Final = (
    "libcrypto-3-x64.dll",  # OpenSSL: no network; hashlib falls back to its built-in SHA-256
    "libssl-3-x64.dll",
    "_ssl.pyd",
    "_hashlib.pyd",
    "_asyncio.pyd",
    "_overlapped.pyd",
    "_multiprocessing.pyd",
    "pyexpat.pyd",
    "select.pyd",
    "_wmi.pyd",
)
"""Python extensions Concentrator never loads (checked at run time, phase 8 review), in ``_internal``."""
TRIMMED_QT_PARTS: Final = (
    "opengl32sw.dll",  # software OpenGL: the widgets paint with the raster engine
    "translations",  # Qt's own texts: Concentrator shows its catalogs only
    "Qt6OpenGL.dll",
    "Qt6MultimediaWidgets.dll",
    "QtMultimediaWidgets.pyd",
    "Qt6Pdf.dll",
    "Qt6Qml.dll",
    "Qt6QmlMeta.dll",
    "Qt6QmlModels.dll",
    "Qt6QmlWorkerScript.dll",
    "Qt6Quick.dll",
    "Qt6VirtualKeyboard.dll",
    "plugins/generic",
    "plugins/networkinformation",
    "plugins/platforminputcontexts",
    "plugins/tls",
    "plugins/platforms/qdirect2d.dll",
    "plugins/platforms/qminimal.dll",
    *(
        f"plugins/imageformats/{name}.dll"
        for name in ("qgif", "qicns", "qjpeg", "qpdf", "qtga", "qtiff", "qwbmp", "qwebp")
    ),
)
"""Qt parts no kept part imports (checked with the PE import tables at phase 8); the ICO and SVG image
plugins, the FFmpeg multimedia plugin and the windows and offscreen platforms stay. The self-check fails if
MP3 decoding or the SVG icons break."""
VERSION_INFO_TEMPLATE: Final = """\
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numbers},
    prodvers={numbers},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0),
  ),
  kids=[
    StringFileInfo([
      StringTable('040904B0', [
        StringStruct('CompanyName', '{company}'),
        StringStruct('FileDescription', '{product}'),
        StringStruct('FileVersion', '{version}'),
        StringStruct('InternalName', '{product}'),
        StringStruct('LegalCopyright', '{copyright}'),
        StringStruct('OriginalFilename', '{product}.exe'),
        StringStruct('ProductName', '{product}'),
        StringStruct('ProductVersion', '{version}'),
      ]),
    ]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])]),
  ],
)
"""


def project_version(pyproject: Path = PYPROJECT_FILE) -> str:
    """Read the version of the project.

    Args:
        pyproject: ``pyproject.toml``.

    Returns:
        ``[project].version``, such as ``"1.0.0"``.
    """
    with pyproject.open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def version_numbers(version: str) -> tuple[int, int, int, int]:
    """Turn a version into the four numbers of a Windows version resource.

    Args:
        version: ``major.minor.patch``, optionally followed by a suffix (``1.0.0rc1``).

    Returns:
        ``(major, minor, patch, 0)``.

    Raises:
        ValueError: If the version does not start with three numbers.
    """
    found = VERSION_PATTERN.match(version)
    if found is None:
        raise ValueError(version)
    major, minor, patch = (int(part) for part in found.groups())
    return major, minor, patch, 0


def version_file_text(version: str) -> str:
    """Build the PyInstaller ``--version-file`` content (a Python expression).

    Args:
        version: Project version.

    Returns:
        The file content.
    """
    return VERSION_INFO_TEMPLATE.format(
        numbers=version_numbers(version), version=version, company=COMPANY_NAME, product=APP_NAME, copyright=COPYRIGHT
    )


def pyinstaller_command(version_file: Path) -> list[str]:
    """Build the PyInstaller command line; every path is absolute (``--specpath`` moves the base).

    Args:
        version_file: Windows version resource.

    Returns:
        The command.
    """
    command = [sys.executable, "-m", "PyInstaller", str(ENTRY_SCRIPT), "--name", APP_NAME]
    command += ["--onedir", "--windowed", "--noupx", "--noconfirm", "--clean"]
    command += ["--icon", str(ICON_FILE), "--specpath", str(BUILD_DIR), "--workpath", str(BUILD_DIR / "work")]
    command += ["--distpath", str(DIST_DIR), "--copy-metadata", "concentrator", "--version-file", str(version_file)]
    for name in BUNDLED_ASSET_DIRS:
        command += ["--add-data", f"{ASSETS_DIR / name}{os.pathsep}assets/{name}"]
    return command


def _size(path: Path) -> int:
    """Size of a file, or of every file in a folder.

    Args:
        path: File or folder.

    Returns:
        Bytes.
    """
    if path.is_file():
        return path.stat().st_size
    return sum(item.stat().st_size for item in path.rglob("*") if item.is_file())


def trim_bundle(app_dir: Path) -> int:
    """Remove the parts Concentrator never loads (``TRIMMED_QT_PARTS``, ``TRIMMED_PYTHON_PARTS``).

    Missing parts are skipped.

    Args:
        app_dir: The onedir folder.

    Returns:
        Bytes removed.
    """
    removed = 0
    parts = (*(QT_DIR / part for part in TRIMMED_QT_PARTS), *(INTERNAL_DIR / part for part in TRIMMED_PYTHON_PARTS))
    for part in parts:
        target = app_dir / part
        if not target.exists():
            continue
        removed += _size(target)
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    return removed


def release_zip(dist_dir: Path, version: str) -> Path:
    """Zip the onedir folder for a release.

    Args:
        dist_dir: Folder that holds ``Concentrator/``.
        version: Project version.

    Returns:
        ``<dist_dir>/Concentrator-<version>-win64.zip``, whose entries start with ``Concentrator/``.
    """
    base_name = dist_dir / f"{APP_NAME}-{version}-{RELEASE_SUFFIX}"
    return Path(shutil.make_archive(str(base_name), "zip", root_dir=dist_dir, base_dir=APP_NAME))


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


def build(version: str) -> bool:
    """Run PyInstaller, trim the bundle and copy the ini.

    Args:
        version: Project version.

    Returns:
        Whether PyInstaller succeeded.
    """
    BUILD_DIR.mkdir(exist_ok=True)
    VERSION_FILE.write_bytes(version_file_text(version).encode("utf-8"))
    print(f"=== PyInstaller ({APP_NAME} {version})", flush=True)
    if subprocess.run(pyinstaller_command(VERSION_FILE), cwd=REPO_ROOT, check=False).returncode != 0:
        print("PyInstaller failed")
        return False
    removed = trim_bundle(APP_DIR)
    left = _size(APP_DIR) / BYTES_PER_MB
    print(f"=== Removed {removed / BYTES_PER_MB:.1f} MB of unused Qt and Python parts; {left:.1f} MB left")
    shutil.copy2(INI_FILE, APP_DIR / INI_FILE.name)
    print(f"=== Copied {INI_FILE.name} next to {EXE_FILE.name}")
    return True


def main(argv: Sequence[str]) -> int:
    """Build, self-check and, with ``--release``, zip.

    Args:
        argv: Command-line arguments.

    Returns:
        0 on success, 1 on failure.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help=f"also write dist/{APP_NAME}-<version>-win64.zip")
    options = parser.parse_args(argv)
    if not ICON_FILE.is_file():
        print(f"Application icon missing: {ICON_FILE}")
        return 1
    version = project_version()
    if not build(version):
        return 1
    exit_code = self_check(EXE_FILE)
    if exit_code != 0:
        print(f"=== Self-check FAILED (exit code {exit_code}); see the log in %LOCALAPPDATA%\\Concentrator\\logs")
        return 1
    print(f"=== Self-check passed: {EXE_FILE}")
    if options.release:
        archive = release_zip(DIST_DIR, version)
        print(f"=== Release archive: {archive} ({archive.stat().st_size / BYTES_PER_MB:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
