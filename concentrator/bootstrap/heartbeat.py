"""The ticker and the Qt timer that drives it (``AGENTS.md`` section 4.3)."""

from collections.abc import Callable
from dataclasses import dataclass

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from concentrator.application.common.app_config import AppConfig
from concentrator.application.common.app_ticker import AppTicker


@dataclass(frozen=True, slots=True)
class Heartbeat:
    """The ticker and the Qt timer that drives it, kept alive together by the shell.

    PySide6 does not keep alive the owner of a bound method connected to a signal: a ticker that only
    the connection references is collected at once, and the timer then fires into nothing (the timer
    never counted down and the chime never played, phase 3 review).

    Attributes:
        ticker: Calls the timer engine, then the chime service.
        timer: Qt timer calling ``ticker.tick`` every ``timer.tick_interval_ms`` (not started).
    """

    ticker: AppTicker
    timer: QTimer


def create_heartbeat(app: QApplication, config: AppConfig, handlers: tuple[Callable[[], None], ...]) -> Heartbeat:
    """Create the ticker and the Qt timer calling it every ``timer.tick_interval_ms`` (not started).

    Args:
        app: Owner of the timer.
        config: Loaded configuration.
        handlers: Called on every tick, in order.

    Returns:
        The heartbeat; the shell keeps it alive.
    """
    ticker = AppTicker()
    for handler in handlers:
        ticker.register(handler)
    timer = QTimer(app)
    timer.setInterval(config.timer.tick_interval_ms)
    timer.timeout.connect(ticker.tick)
    return Heartbeat(ticker=ticker, timer=timer)
