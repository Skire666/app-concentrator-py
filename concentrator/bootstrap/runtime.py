"""Process-wide services installed once the configuration is known: logging, hooks, Qt log bridge."""

import sys
from typing import override

from concentrator.application.common.app_config import AppConfig
from concentrator.application.ports.error_reporter_port import ErrorReporterPort
from concentrator.infrastructure.logging.exception_hooks import ExceptionHooks
from concentrator.infrastructure.logging.logging_setup import LoggingRuntime, configure_logging
from concentrator.infrastructure.qt.qt_log_bridge import QtLogBridge


class ForwardingErrorReporter(ErrorReporterPort):
    """Reporter installed with the hooks before the window exists; forwards once a target is set."""

    def __init__(self) -> None:
        """Create a reporter without target (errors are then only logged by the caller)."""
        self._target: ErrorReporterPort | None = None

    def connect(self, target: ErrorReporterPort) -> None:
        """Start forwarding.

        Args:
            target: The error dialog presenter.
        """
        self._target = target

    @override
    def report(self, error: BaseException) -> None:
        if self._target is not None:
            self._target.report(error)


class Runtime:
    """Installed services; ``shutdown`` removes them in reverse order and flushes the log."""

    def __init__(
        self,
        logging_runtime: LoggingRuntime,
        hooks: ExceptionHooks,
        bridge: QtLogBridge,
        reporter: ForwardingErrorReporter,
    ) -> None:
        """Keep the installed services.

        Args:
            logging_runtime: Root logger handlers.
            hooks: Global exception hooks.
            bridge: Qt message handler.
            reporter: Reporter shared by the hooks and the event bus.
        """
        self.logging = logging_runtime
        self.reporter = reporter
        self._hooks = hooks
        self._bridge = bridge

    def shutdown(self) -> None:
        """Uninstall the hooks and the Qt bridge, then flush and close the log."""
        self._hooks.uninstall()
        self._bridge.uninstall()
        self.logging.shutdown()


def configure_runtime(config: AppConfig) -> Runtime:
    """Configure logging, exception hooks, the Qt message bridge and ``faulthandler`` (startup step 3).

    Args:
        config: Loaded configuration.

    Returns:
        The installed services.
    """
    logging_runtime = configure_logging(config.logging, config.paths.log_dir, stream=sys.stderr)
    reporter = ForwardingErrorReporter()
    hooks = ExceptionHooks(reporter)
    hooks.install()
    bridge = QtLogBridge()
    bridge.install()
    return Runtime(logging_runtime, hooks, bridge, reporter)
