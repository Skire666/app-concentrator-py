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


def test_only_the_toml_codec_imports_tomllib() -> None:
    importers = sorted(relative(path) for path in source_files() if "tomllib" in _imported_modules(parse(path)))

    assert importers == ["concentrator/infrastructure/persistence/toml_codec.py"]


def test_domain_focus_imports_only_identifiers_of_domain_todo() -> None:
    allowed = {("concentrator.domain.todo.task", "TaskId")}
    imported: list[str] = []
    for path in source_files():
        if not relative(path).startswith("concentrator/domain/focus/"):
            continue
        for node in ast.walk(parse(path)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").startswith("concentrator.domain.todo"):
                imported.extend(
                    f"{relative(path)}: {node.module}.{alias.name}"
                    for alias in node.names
                    if (node.module, alias.name) not in allowed
                )
    assert imported == []
