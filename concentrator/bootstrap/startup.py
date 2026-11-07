"""Startup step inserted after the catalogs (ADR-027): language hint, unguarded warning, data file."""

import logging

from PySide6.QtGui import QIcon

from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.storage import Storage
from concentrator.presentation.common.date_time_formatter import DateTimeFormatter
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter
from concentrator.presentation.storage.startup_dialog_layout import StartupDialogLayout
from concentrator.presentation.storage.startup_flow_presenter import StartupFlowPresenter
from concentrator.ui.support.modal_host import ScreenDialogRunner
from concentrator.ui.support.qt_dialog_service import QtDialogService
from concentrator.ui.windows.startup_dialogs import StartupDialogs

_logger = logging.getLogger(__name__)


def apply_language_hint(storage: Storage, translator: TranslatorPort) -> None:
    """Show the startup dialogs in the language last used, when one is remembered.

    Args:
        storage: Storage services (the hint).
        translator: Translator still in ``i18n.default_language``.
    """
    hint = storage.hint.read()
    if not hint.is_set:
        return
    result = translator.set_language(hint)
    if result.is_failure:
        _logger.warning("Language hint %s not applied: %s", hint.name, [code.name for code in result.error_codes])


def open_data_file(
    core: Core,
    storage: Storage,
    translator: TranslatorPort,
    instance: InstanceProtectionPresenter,
    icon: QIcon,
    layout: StartupDialogLayout,
) -> bool:
    """Warn when unguarded, then resolve the data file through the startup dialogs.

    Args:
        core: Main-thread services.
        storage: Storage services.
        translator: Current-language translator.
        instance: Unguarded single-instance warning.
        icon: Window icon of the dialogs.
        layout: Sizes of the dialogs (``[ui]``).

    Returns:
        Whether a data file is open (``False``: the user quit).
    """
    apply_language_hint(storage, translator)
    dialogs = QtDialogService(ScreenDialogRunner())
    instance.warn_if_unprotected(dialogs)
    flow = StartupFlowPresenter(
        commands=storage.startup,
        dialogs=dialogs,
        gate=core.gate,
        renderer=core.renderer,
        translator=translator,
        formatter=DateTimeFormatter(translator, core.clock),
    )
    flow.attach(StartupDialogs(flow, core.renderer, icon, layout))
    if not flow.run():
        return False
    settings = storage.settings_queries.current_settings()
    if settings.data is not None:
        storage.switcher.follow(settings.data.language)
    return True
