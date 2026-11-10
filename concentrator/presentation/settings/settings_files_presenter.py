"""Data file, Interface and About sections of the settings page: commands that act at once."""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from concentrator.application.ports.link_opener_port import LinkOpenerPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.domain.common.validation_result import ValidationResult
from concentrator.presentation.common.action_button import action_button
from concentrator.presentation.common.action_gate import ActionGate
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.button_snapshot import ButtonSnapshot
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.common.pending_edits import PendingEdits
from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.common.ui_texts import UiTexts
from concentrator.presentation.ports.dialog_port import DialogPort
from concentrator.presentation.settings.about_info import AboutInfo
from concentrator.presentation.settings.data_file_flow import DataFileFlow
from concentrator.presentation.settings.settings_folder_enum import SettingsFolderEnum
from concentrator.presentation.settings.settings_snapshot import (
    AboutSectionSnapshot,
    DataFileSectionSnapshot,
    InterfaceSectionSnapshot,
    PathRowSnapshot,
    SettingsFilesSnapshot,
)

_logger = logging.getLogger(__name__)

type LayoutResetListener = Callable[[], None]


@dataclass(frozen=True, slots=True, kw_only=True)
class SettingsFilesServices:
    """What the file sections read and drive.

    Attributes:
        data_file: "Use another file..." and "Move file...".
        current_path: Path of the open data file, ``None`` before one is open.
        opener: Opens the folders.
        layout: Removes the ``layout/*`` keys.
        about: Version and locations.
    """

    data_file: DataFileFlow
    current_path: Callable[[], Path | None]
    opener: LinkOpenerPort
    layout: LayoutStateKeeper
    about: AboutInfo


class SettingsFilesPresenter:
    """Builds the file sections of ``SETTINGS`` and runs their commands; it has no draft."""

    def __init__(
        self, translator: TranslatorPort, gate: ActionGate, renderer: RenderCoordinator, services: SettingsFilesServices
    ) -> None:
        """Create the presenter.

        Args:
            translator: Current-language translator.
            gate: Runs every user action.
            renderer: Receives the render requests.
            services: Data file flow, folder opener, layout store and About facts.
        """
        self._translator = translator
        self._texts = UiTexts(translator)
        self._gate = gate
        self._renderer = renderer
        self._services = services
        self._dialogs: DialogPort | None = None
        self._reset_listeners: list[LayoutResetListener] = []
        self._actions: dict[ActionIdEnum, Callable[[], ValidationResult]] = {
            ActionIdEnum.SETTINGS_SWITCH_DATA_FILE: services.data_file.switch,
            ActionIdEnum.SETTINGS_MOVE_DATA_FILE: services.data_file.move,
            ActionIdEnum.SETTINGS_RESET_LAYOUT: self._reset_layout,
        }

    def attach(self, dialogs: DialogPort, edits: PendingEdits) -> None:
        """Set the dialog service of the main window (ADR-036) and the settings form.

        Args:
            dialogs: Questions and messages.
            edits: The settings form, resolved before another data file opens.
        """
        self._dialogs = dialogs
        self._services.data_file.attach(dialogs, edits)

    def add_layout_reset_listener(self, listener: LayoutResetListener) -> None:
        """Call a function after "Reset layout" removed the stored layout (it applies the defaults).

        Args:
            listener: Applies the default layout of a window or page.
        """
        self._reset_listeners.append(listener)

    def build_snapshot(self) -> SettingsFilesSnapshot:
        """Describe the Data file, Interface and About sections.

        Returns:
            The snapshot.
        """
        tr = self._translator.tr
        current = self._services.current_path()
        return SettingsFilesSnapshot(
            data_file=DataFileSectionSnapshot(
                title=tr("settings.section.data_file"),
                current=self._path_row("settings.data_file.path", current, SettingsFolderEnum.DATA_FILE),
                hint=tr("settings.data_file.hint"),
                switch=self._button(ActionIdEnum.SETTINGS_SWITCH_DATA_FILE),
                move=self._button(ActionIdEnum.SETTINGS_MOVE_DATA_FILE, enabled=current is not None),
            ),
            interface=InterfaceSectionSnapshot(
                title=tr("settings.section.interface"),
                hint=tr("settings.interface.hint"),
                reset_layout=self._button(ActionIdEnum.SETTINGS_RESET_LAYOUT),
            ),
            about=self._about(),
        )

    def _about(self) -> AboutSectionSnapshot:
        """Describe the About section.

        Returns:
            Version and locations.
        """
        tr = self._translator.tr
        about = self._services.about
        return AboutSectionSnapshot(
            title=tr("settings.section.about"),
            version_label=tr("settings.about.version"),
            version=about.version,
            paths=(
                self._path_row("settings.about.app_config", about.app_config_file, SettingsFolderEnum.APP_CONFIG),
                self._path_row("settings.about.ui_state", about.ui_state_file, SettingsFolderEnum.UI_STATE),
                self._path_row("settings.about.log_dir", about.log_dir, SettingsFolderEnum.LOG),
                self._path_row("settings.about.backup_dir", about.backup_dir, SettingsFolderEnum.BACKUP),
            ),
        )

    def on_action_requested(self, action_value: int) -> None:
        """Handle "Use another file...", "Move file..." and "Reset layout".

        Args:
            action_value: ``ActionIdEnum`` value emitted by the panel.
        """
        action = ActionIdEnum.parse(action_value)
        operation = self._actions.get(action)
        if operation is None:
            _logger.warning("Settings file action %s (%d) is not handled", action.name, action_value)
            return
        result = self._gate.run(action, operation, interactive=True)
        if result.is_failure:
            _logger.warning("Settings file action %s: %s", action.name, [code.name for code in result.error_codes])
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def on_open_folder(self, folder_value: int) -> None:
        """Open a folder in the file explorer; a missing application folder is created first.

        Args:
            folder_value: ``SettingsFolderEnum`` value of the clicked button.
        """
        folder = SettingsFolderEnum.parse(folder_value)
        self._gate.run(ActionIdEnum.SETTINGS_OPEN_FOLDER, lambda: self._open_folder(folder))
        self._renderer.request(RenderSectionEnum.SETTINGS)

    def _open_folder(self, folder: SettingsFolderEnum) -> ValidationResult:
        """Open one folder.

        Args:
            folder: Which one.

        Returns:
            The opener result (a refusal is a logged warning), or skipped for an unknown folder.
        """
        about = self._services.about
        current = self._services.current_path()
        targets: dict[SettingsFolderEnum, tuple[Path | None, bool]] = {
            SettingsFolderEnum.DATA_FILE: (None if current is None else current.parent, False),
            SettingsFolderEnum.APP_CONFIG: (about.app_config_file.parent, False),
            SettingsFolderEnum.UI_STATE: (about.ui_state_file.parent, True),
            SettingsFolderEnum.LOG: (about.log_dir, True),
            SettingsFolderEnum.BACKUP: (about.backup_dir, True),
        }
        path, create_missing = targets.get(folder, (None, False))
        if path is None:
            _logger.warning("Folder %s cannot be opened", folder.name)
            return ValidationResult.skipped()
        return self._services.opener.open_folder(path, create_missing=create_missing)

    def _reset_layout(self) -> ValidationResult:
        """Remove the stored layout after a confirmation and apply the defaults at once.

        Returns:
            Success, or skipped when the user cancelled.
        """
        tr = self._translator.tr
        if self._dialogs is None or not self._dialogs.confirm(
            tr("action.settings_reset_layout"),
            tr("settings.reset_layout.message"),
            tr("dialog.button.reset"),
            tr("dialog.button.cancel"),
        ):
            return ValidationResult.skipped()
        self._services.layout.reset()
        for listener in self._reset_listeners:
            listener()
        _logger.info("Layout reset to the defaults")
        return ValidationResult.success()

    def _path_row(self, label_key: str, path: Path | None, folder: SettingsFolderEnum) -> PathRowSnapshot:
        """Describe a path with its "Open folder" button.

        Args:
            label_key: Catalog key of the label.
            path: The path, ``None`` when unknown.
            folder: Folder opened by the button.

        Returns:
            The row snapshot.
        """
        return PathRowSnapshot(
            label=self._translator.tr(label_key),
            path="" if path is None else path.as_posix(),
            folder=int(folder),
            open_folder=self._button(ActionIdEnum.SETTINGS_OPEN_FOLDER, enabled=path is not None),
        )

    def _button(self, action: ActionIdEnum, *, enabled: bool = True) -> ButtonSnapshot:
        """Describe a button of the file sections.

        Args:
            action: Its action.
            enabled: Whether the current state allows it.

        Returns:
            The button snapshot.
        """
        return action_button(self._texts, self._gate, action, enabled=enabled)
