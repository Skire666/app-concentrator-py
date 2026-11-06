"""Configuration error shown before logging and catalogs exist (startup step 3).

These are the only literal UI texts of the application (plain English, spec phase 0, ADR-024): the
catalogs cannot be relied on while the configuration itself is broken.
"""

from pathlib import Path
from typing import Final

from PySide6.QtWidgets import QMessageBox

from concentrator.domain.common.validation_result import ValidationResult

CONFIG_ERROR_TITLE: Final = "Concentrator cannot start"
CONFIG_ERROR_INTRO: Final = "The configuration file is missing or invalid:"
CONFIG_ERROR_HINT: Final = "Fix or restore this file, then start Concentrator again."


def format_config_error(validation: ValidationResult, config_file: Path) -> str:
    """Describe a configuration failure: the ini path and one line per issue.

    Args:
        validation: Failure returned by ``IniConfigLoader``.
        config_file: Path of ``concentrator.ini``.

    Returns:
        Plain English text.
    """
    lines = [
        f"- {issue.code.name} ({issue.code.value})" + (f": {issue.field}" if issue.field else "")
        for issue in validation.issues
    ]
    return "\n".join([CONFIG_ERROR_INTRO, str(config_file), "", *lines, "", CONFIG_ERROR_HINT])


def show_config_error(validation: ValidationResult, config_file: Path) -> None:
    """Show the configuration failure in a modal message box.

    Args:
        validation: Failure returned by ``IniConfigLoader``.
        config_file: Path of ``concentrator.ini``.
    """
    QMessageBox.critical(None, CONFIG_ERROR_TITLE, format_config_error(validation, config_file))
