import logging

import pytest

from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.presentation.common.action_id_enum import ActionIdEnum
from concentrator.presentation.common.render_section_enum import RenderSectionEnum
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.shell.shell_snapshot import StatusBarSnapshot
from concentrator.presentation.shell.status_bar_presenter import StatusBarPresenter
from concentrator.presentation.storage.save_status_texts import SaveStatusTexts
from tests.fakes.storage_stack import DATA_PATH, StorageStack
from tests.fakes.user_data_factory import SAVED_AT, make_user_data


class Setup:
    def __init__(self, *, protected: bool = True) -> None:
        self.stack = StorageStack()
        self.instance = InstanceProtectionPresenter(self.stack.translator, protected=protected)
        self.presenter = StatusBarPresenter(
            self.stack.translator,
            self.stack.gate,
            self.stack.renderer,
            switcher=self.stack.switcher,
            save_texts=SaveStatusTexts(self.stack.translator, self.stack.formatter),
            coordinator=self.stack.coordinator,
            instance=self.instance,
        )
        self.rendered: list[StatusBarSnapshot] = []
        self.stack.renderer.register(RenderSectionEnum.STATUS_BAR, self.presenter.build_snapshot, self.rendered.append)

    def flush(self) -> StatusBarSnapshot:
        self.stack.renderer.flush()
        return self.presenter.build_snapshot()


def test_snapshot_without_file_and_protected() -> None:
    snapshot = Setup().presenter.build_snapshot()

    assert snapshot.save_state_text == "en:status.save.no_file"
    assert not snapshot.save_state_tooltip
    assert not snapshot.instance_warning_text
    assert not snapshot.instance_warning_tooltip
    assert snapshot.language_button.text == "en:shell.language.button.en"
    assert snapshot.language_button.action is ActionIdEnum.SHELL_TOGGLE_LANGUAGE


def test_unprotected_mode_shows_the_indicator() -> None:
    snapshot = Setup(protected=False).presenter.build_snapshot()

    assert snapshot.instance_warning_text == "en:status.instance.unguarded"
    assert snapshot.instance_warning_tooltip == "en:instance.unguarded.message"


def test_save_status_change_re_renders_the_status_bar() -> None:
    setup = Setup()
    setup.stack.session.reset(make_user_data())
    setup.stack.coordinator.attach(DATA_PATH, SAVED_AT)

    setup.presenter.on_save_status_changed(setup.stack.coordinator.status)
    setup.stack.renderer.flush()

    assert setup.rendered[-1].save_state_text.startswith("en:status.save.saved_at(")
    assert setup.rendered[-1].save_state_tooltip == "en:status.save.tooltip.path(path=D:/sync/concentrator.toml)"


def test_language_button_toggles_through_the_gate() -> None:
    setup = Setup()

    setup.presenter.on_action_requested(int(ActionIdEnum.SHELL_TOGGLE_LANGUAGE))

    assert setup.stack.translator.language is LanguageEnum.FRENCH
    assert not setup.presenter.build_snapshot().language_button.enabled
    setup.stack.after_cooldown()
    assert setup.flush().language_button.text == "fr:shell.language.button.fr"
    assert setup.presenter.build_snapshot().language_button.enabled


def test_failed_toggle_is_logged(caplog: pytest.LogCaptureFixture) -> None:
    setup = Setup()
    setup.stack.translator.refused = frozenset({LanguageEnum.FRENCH})

    setup.presenter.on_action_requested(int(ActionIdEnum.SHELL_TOGGLE_LANGUAGE))

    assert "Language toggle failed" in caplog.text


def test_other_actions_are_ignored(caplog: pytest.LogCaptureFixture) -> None:
    setup = Setup()

    with caplog.at_level(logging.WARNING):
        setup.presenter.on_action_requested(int(ActionIdEnum.SHELL_SHOW_JOURNAL))

    assert "not handled" in caplog.text
    assert setup.stack.translator.language is LanguageEnum.ENGLISH


def test_instance_warning_dialog_only_when_unprotected() -> None:
    protected = Setup()
    unprotected = Setup(protected=False)

    protected.instance.warn_if_unprotected(protected.stack.dialogs)
    unprotected.instance.warn_if_unprotected(unprotected.stack.dialogs)

    assert protected.stack.dialogs.calls == []
    assert protected.instance.protected
    assert unprotected.stack.dialogs.texts("warn") == [
        ("en:instance.unguarded.title", "en:instance.unguarded.message", "en:dialog.button.ok")
    ]
