"""Wiring of the journal page (Menu B): presenter on top of the in-memory log buffer."""

from concentrator.application.common.app_config import AppConfig
from concentrator.application.journal.journal_queries import JournalQueries
from concentrator.application.ports.log_feed_port import LogFeedPort
from concentrator.application.ports.translator_port import TranslatorPort
from concentrator.bootstrap.core import Core
from concentrator.infrastructure.qt.qt_link_opener import QtLinkOpener
from concentrator.presentation.common.layout_state_keeper import LayoutStateKeeper
from concentrator.presentation.journal.journal_presenter import JournalPorts, JournalPresenter, JournalSettings
from concentrator.ui.support.qt_clipboard import QtClipboard


def build_journal(config: AppConfig, translator: TranslatorPort, core: Core, feed: LogFeedPort) -> JournalPresenter:
    """Create the journal presenter.

    Args:
        config: Loaded configuration (``[journal]``, log folder, buffer size).
        translator: Current-language translator.
        core: Main-thread services.
        feed: The in-memory log buffer.

    Returns:
        The presenter; the shell registers its tick and its page listener.
    """
    ports = JournalPorts(
        queries=JournalQueries(feed),
        clock=core.clock,
        scheduler=core.scheduler,
        clipboard=QtClipboard(),
        opener=QtLinkOpener(),
        layout=LayoutStateKeeper(core.preferences),
    )
    settings = JournalSettings(
        log_dir=config.paths.log_dir,
        capacity=config.logging.journal_buffer_size,
        search_debounce_ms=config.journal.search_debounce_ms,
        copy_max_rows=config.journal.copy_max_rows,
    )
    return JournalPresenter(translator, core.gate, core.renderer, ports, settings)
