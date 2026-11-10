"""Read-only facts shown in the About section of the settings page."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True, kw_only=True)
class AboutInfo:
    """Version and locations of the installation.

    Attributes:
        version: Installed version.
        app_config_file: ``concentrator.ini``.
        ui_state_file: ``paths.ui_state_file``.
        log_dir: ``paths.log_dir``.
        backup_dir: ``paths.backup_dir``.
    """

    version: str
    app_config_file: Path
    ui_state_file: Path
    log_dir: Path
    backup_dir: Path
