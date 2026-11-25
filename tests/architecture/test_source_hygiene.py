import ast

from tests.architecture.source_tree import PACKAGE_ROOT, parse, relative, source_files


def test_source_tree_is_not_empty() -> None:
    assert len(source_files()) > 1


def test_no_print_call_in_source() -> None:
    offenders = [
        f"{relative(path)}:{node.lineno}"
        for path in source_files()
        for node in ast.walk(parse(path))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "print"
    ]

    assert offenders == []


def test_every_source_directory_is_a_package() -> None:
    directories = {
        directory for path in source_files() for directory in path.parents if directory.is_relative_to(PACKAGE_ROOT)
    }

    missing = sorted(relative(directory) for directory in directories if not (directory / "__init__.py").is_file())

    assert missing == []


def _imported_modules(tree: ast.Module) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            names.add(node.module)
    return names


def test_no_module_imports_qt_multimedia() -> None:
    importers = sorted(
        relative(path)
        for path in source_files()
        if any(name.startswith("PySide6.QtMultimedia") for name in _imported_modules(parse(path)))
    )

    assert importers == []


def test_only_the_audio_adapter_imports_miniaudio() -> None:
    importers = sorted(relative(path) for path in source_files() if "miniaudio" in _imported_modules(parse(path)))

    assert importers == ["concentrator/infrastructure/audio/miniaudio_sound_player.py"]


def test_only_the_toml_codec_imports_tomllib() -> None:
    importers = sorted(relative(path) for path in source_files() if "tomllib" in _imported_modules(parse(path)))

    assert importers == ["concentrator/infrastructure/persistence/toml_codec.py"]


_WRITE_METHODS = frozenset({"write_text", "write_bytes", "rename", "unlink", "touch", "symlink_to", "hardlink_to"})
_WRITE_MODULE_FUNCTIONS = frozenset(
    {
        ("os", "replace"),
        ("os", "remove"),
        ("os", "rename"),
        ("os", "unlink"),
        ("shutil", "copy"),
        ("shutil", "copy2"),
        ("shutil", "copyfile"),
        ("shutil", "move"),
        ("shutil", "rmtree"),
    }
)
_WRITE_MODE_CHARACTERS = frozenset("wax+")
_FILE_WRITERS = [
    "concentrator/infrastructure/logging/logging_setup.py",
    "concentrator/infrastructure/persistence/atomic_file_writer.py",
    "concentrator/infrastructure/persistence/daily_backup.py",
    "concentrator/infrastructure/persistence/toml_user_data_file.py",
]


def _open_mode(call: ast.Call) -> str:
    keyword = next((item.value for item in call.keywords if item.arg == "mode"), None)
    position = 0 if isinstance(call.func, ast.Attribute) else 1
    value = keyword if keyword is not None else (call.args[position] if len(call.args) > position else None)
    return value.value if isinstance(value, ast.Constant) and isinstance(value.value, str) else ""


def _writes_files(node: ast.AST) -> bool:
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and (node.value.id, node.attr) in _WRITE_MODULE_FUNCTIONS
    ):
        return True
    if not isinstance(node, ast.Call):
        return False
    name = node.func.attr if isinstance(node.func, ast.Attribute) else getattr(node.func, "id", "")
    if name in _WRITE_METHODS:
        return True
    return name == "open" and bool(_WRITE_MODE_CHARACTERS & set(_open_mode(node)))


def test_only_the_storage_adapters_and_the_log_setup_write_files() -> None:
    writers = sorted(
        relative(path) for path in source_files() if any(_writes_files(node) for node in ast.walk(parse(path)))
    )

    assert writers == _FILE_WRITERS
