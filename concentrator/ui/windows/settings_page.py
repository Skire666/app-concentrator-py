"""Menu C page: the settings form and the file commands in a scroll area, Save and Revert below.

The mouse wheel always scrolls the page, even over a list, a spin box or a slider (ADR-041).
"""

from PySide6.QtWidgets import QFrame, QScrollArea, QVBoxLayout, QWidget

from concentrator.presentation.common.render_coordinator import RenderCoordinator
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.settings.settings_files_presenter import SettingsFilesPresenter
from concentrator.presentation.settings.settings_presenter import SettingsPresenter
from concentrator.presentation.settings.settings_snapshot import SettingsSnapshot
from concentrator.ui.panels.settings_files_panel import SettingsFilesPanel
from concentrator.ui.panels.settings_footer_panel import SettingsFooterPanel
from concentrator.ui.panels.settings_form_panel import SettingsFormPanel
from concentrator.ui.support.wheel_scroll_redirect import WheelScrollRedirect


class SettingsPage(QWidget):
    """Sections in a scroll area; the footer with Save and Revert stays visible."""

    def __init__(self, spacing_px: int, parent: QWidget | None = None) -> None:
        """Build the page.

        Args:
            spacing_px: ``ui.dialog_spacing_px``.
            parent: Parent widget.
        """
        super().__init__(parent)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget(scroll)
        self._form = SettingsFormPanel(spacing_px, content)
        self._files = SettingsFilesPanel(spacing_px, content)
        sections = QVBoxLayout(content)
        sections.setSpacing(spacing_px)
        sections.addWidget(self._form)
        sections.addWidget(self._files)
        sections.addStretch(1)
        scroll.setWidget(content)
        WheelScrollRedirect(scroll).watch(content)
        self._footer = SettingsFooterPanel(self)
        page = QVBoxLayout(self)
        page.addWidget(scroll, 1)
        page.addWidget(self._footer)

    @property
    def form(self) -> SettingsFormPanel:
        """General and Hourly chime sections (for tests)."""
        return self._form

    @property
    def files(self) -> SettingsFilesPanel:
        """Data file, Interface and About sections (for tests)."""
        return self._files

    @property
    def footer(self) -> SettingsFooterPanel:
        """Save, Revert and the unsaved changes text (for tests)."""
        return self._footer

    def connect_presenters(
        self, presenter: SettingsPresenter, files: SettingsFilesPresenter, renderer: RenderCoordinator
    ) -> None:
        """Wire the panels to their presenters and register the ``SETTINGS`` section.

        Args:
            presenter: Settings form presenter (builds the whole snapshot).
            files: File sections presenter.
            renderer: Render coordinator.
        """
        form = self._form
        form.language_selected.connect(presenter.on_language_selected)
        form.log_level_selected.connect(presenter.on_log_level_selected)
        form.notify_toggled.connect(presenter.on_notify_toggled)
        form.chime_enabled_toggled.connect(presenter.on_chime_enabled_toggled)
        form.sound_selected.connect(presenter.on_sound_selected)
        form.volume_changed.connect(presenter.on_volume_changed)
        form.start_hour_changed.connect(presenter.on_start_hour_changed)
        form.end_hour_changed.connect(presenter.on_end_hour_changed)
        form.action_requested.connect(presenter.on_action_requested)
        self._footer.action_requested.connect(presenter.on_action_requested)
        self._files.action_requested.connect(files.on_action_requested)
        self._files.open_requested.connect(files.on_open_folder)
        renderer.register(RenderSectionEnum.SETTINGS, presenter.build_snapshot, self.render_snapshot)

    def render_snapshot(self, snapshot: SettingsSnapshot) -> None:
        """Show the page state.

        Args:
            snapshot: Settings state.
        """
        self.setUpdatesEnabled(False)
        self._form.render_snapshot(snapshot.form)
        self._files.render_snapshot(snapshot.files)
        self._footer.render_snapshot(snapshot.form)
        self.setUpdatesEnabled(True)
