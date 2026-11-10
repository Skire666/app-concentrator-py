"""Services built before the main window that the shell needs."""

from dataclasses import dataclass

from concentrator.application.ports.log_feed_port import LogFeedPort
from concentrator.bootstrap.core import Core
from concentrator.bootstrap.startup import StartupFlow
from concentrator.bootstrap.storage import Storage
from concentrator.presentation.shell.instance_protection_presenter import InstanceProtectionPresenter


@dataclass(frozen=True, slots=True, kw_only=True)
class ShellServices:
    """What the startup built and the window uses.

    Attributes:
        core: Main-thread services.
        storage: Storage services.
        instance: Unguarded single-instance indicator.
        feed: In-memory log buffer read by the journal page.
        startup: Startup flow, reused for the recovery of a file chosen on the settings page; ``None``
            when the shell is built without it (tests).
    """

    core: Core
    storage: Storage
    instance: InstanceProtectionPresenter
    feed: LogFeedPort
    startup: StartupFlow | None = None
