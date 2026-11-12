"""The pure steps of ``scripts/build.py`` (phase 8): version resource, trimmed Qt parts, release zip."""

import ast
import zipfile
from pathlib import Path

import pytest

from scripts.build import (
    APP_NAME,
    INTERNAL_DIR,
    QT_DIR,
    TRIMMED_QT_PARTS,
    project_version,
    pyinstaller_command,
    release_zip,
    trim_bundle,
    version_file_text,
    version_numbers,
)


def test_project_version_is_read_from_pyproject(tmp_path: Path) -> None:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "concentrator"\nversion = "1.2.3"\n', encoding="utf-8")

    assert project_version(pyproject) == "1.2.3"


@pytest.mark.parametrize(
    ("version", "numbers"), [("1.0.0", (1, 0, 0, 0)), ("0.1.0", (0, 1, 0, 0)), ("2.10.3rc1", (2, 10, 3, 0))]
)
def test_version_numbers_fill_the_four_windows_fields(version: str, numbers: tuple[int, int, int, int]) -> None:
    assert version_numbers(version) == numbers


def test_version_numbers_refuse_a_version_without_three_numbers() -> None:
    with pytest.raises(ValueError, match=r"1\.0"):
        version_numbers("1.0")


def test_version_file_is_a_python_expression_with_product_and_version() -> None:
    text = version_file_text("1.0.0")

    ast.parse(text, mode="eval")
    assert "filevers=(1, 0, 0, 0)" in text
    assert "StringStruct('ProductVersion', '1.0.0')" in text
    assert "StringStruct('ProductName', 'Concentrator')" in text
    assert "StringStruct('CompanyName', 'skire666')" in text
    assert "StringStruct('OriginalFilename', 'Concentrator.exe')" in text


def test_pyinstaller_leaves_qt_multimedia_out(tmp_path: Path) -> None:
    command = pyinstaller_command(tmp_path / "version_info.txt")

    excluded = [command[index + 1] for index, item in enumerate(command) if item == "--exclude-module"]
    assert excluded == ["PySide6.QtMultimedia", "PySide6.QtMultimediaWidgets"]
    assert command[command.index("--hidden-import") + 1] == "_cffi_backend"


def test_pyinstaller_receives_the_version_file(tmp_path: Path) -> None:
    command = pyinstaller_command(tmp_path / "version_info.txt")

    assert command[command.index("--version-file") + 1] == str(tmp_path / "version_info.txt")


def test_trim_removes_the_listed_qt_parts_and_keeps_the_others(tmp_path: Path) -> None:
    qt = tmp_path / QT_DIR
    kept = [qt / "Qt6Core.dll", qt / "plugins/imageformats/qsvg.dll", qt / "plugins/platforms/qwindows.dll"]
    trimmed = [
        qt / "opengl32sw.dll",
        qt / "translations/qtbase_fr.qm",
        qt / "plugins/imageformats/qpdf.dll",
        tmp_path / INTERNAL_DIR / "libcrypto-3-x64.dll",
        tmp_path / INTERNAL_DIR / "_ssl.pyd",
    ]
    kept.append(tmp_path / INTERNAL_DIR / "python314.dll")
    for path in (*kept, *trimmed):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"1234")

    removed = trim_bundle(tmp_path)

    assert removed == len(trimmed) * 4
    assert all(path.exists() for path in kept)
    assert not any(path.exists() for path in trimmed)
    assert not (qt / "translations").exists()


def test_trim_list_never_names_a_part_the_self_check_needs() -> None:
    needed = {"plugins/imageformats/qsvg.dll", "plugins/imageformats/qico.dll", "plugins/platforms", "Qt6Svg.dll"}

    assert needed.isdisjoint(TRIMMED_QT_PARTS)


def test_release_zip_holds_the_onedir_folder(tmp_path: Path) -> None:
    app_dir = tmp_path / APP_NAME
    (app_dir / "_internal").mkdir(parents=True)
    (app_dir / f"{APP_NAME}.exe").write_bytes(b"exe")
    (app_dir / "concentrator.ini").write_text("[app]\n", encoding="utf-8")

    archive = release_zip(tmp_path, "1.0.0")

    assert archive == tmp_path / "Concentrator-1.0.0-win64.zip"
    with zipfile.ZipFile(archive) as content:
        names = content.namelist()
    assert "Concentrator/Concentrator.exe" in names
    assert "Concentrator/concentrator.ini" in names
