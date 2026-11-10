"""Locating, opening, creating and recovering the data file at startup (ADR-027)."""

import logging
from pathlib import Path
from typing import Final

from concentrator.application.ports.user_data_file_port import UserDataFilePort
from concentrator.application.ports.user_data_session_port import UserDataSessionPort
from concentrator.application.ports.view_preferences_port import ViewPreferencesPort
from concentrator.application.storage.recovery_source_enum import RecoverySourceEnum
from concentrator.application.storage.save_coordinator import SaveCoordinator
from concentrator.application.storage.startup_plan import StartupPlan, classify
from concentrator.application.storage.startup_reason_enum import StartupReasonEnum
from concentrator.application.storage.startup_step_enum import StartupStepEnum
from concentrator.application.storage.user_data import StoredUserData
from concentrator.application.storage.user_data_defaults import UserDataDefaults
from concentrator.domain.common.data_result import DataResult
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings_rules import UserSettingsRules

_logger = logging.getLogger(__name__)

DATA_FILE_PATH_KEY: Final = "storage/data_file_path"


class StartupCommands:
    """Every action of the first-run and recovery dialogs. A plan with step ``READY`` means the file is open.

    Opening a file resets the session, attaches the save coordinator and remembers the path in
    ``ui-state.ini`` (``storage/data_file_path``), only after success.
    """

    def __init__(
        self,
        *,
        file: UserDataFilePort,
        session: UserDataSessionPort,
        coordinator: SaveCoordinator,
        preferences: ViewPreferencesPort,
        defaults: UserDataDefaults,
        default_path: Path,
    ) -> None:
        """Create the use cases.

        Args:
            file: Data file adapter.
            session: In-memory data.
            coordinator: Starts saving once a file is open.
            preferences: ``ui-state.ini`` (remembered path).
            defaults: Settings and sections of a new file, and sections missing from an older file.
            default_path: ``paths.default_data_file``.
        """
        self._file = file
        self._session = session
        self._coordinator = coordinator
        self._preferences = preferences
        self._defaults = defaults
        self._default_path = default_path

    def resolve_startup(self) -> StartupPlan:
        """Inspect the remembered data file, or report a first run.

        Returns:
            The plan; ``READY`` when the remembered file opened.
        """
        remembered = self._preferences.get_text(DATA_FILE_PATH_KEY)
        if remembered is None or not remembered.strip():
            _logger.info("No remembered data file: first run")
            return StartupPlan(
                step=StartupStepEnum.NEEDS_LOCATION,
                reason=StartupReasonEnum.FIRST_RUN,
                path=None,
                default_path=self._default_path,
                default_exists=self._file.exists(self._default_path),
            )
        return self.inspect(Path(remembered))

    def inspect(self, path: Path) -> StartupPlan:
        """Inspect a data file and open it when it is ready ("Open existing file", "Retry").

        Args:
            path: Data file path.

        Returns:
            The plan for that file.
        """
        report = self._file.probe(path)
        if report.data is None:
            return StartupPlan(
                step=StartupStepEnum.FATAL,
                reason=StartupReasonEnum.FILE_UNREADABLE,
                path=path,
                default_path=self._default_path,
                default_exists=self._file.exists(self._default_path),
                problem=report.validation,
            )
        plan = classify(
            report.data, default_path=self._default_path, default_exists=self._file.exists(self._default_path)
        )
        _logger.info("Data file %s: %s (%s)", path, plan.step.name, plan.reason.name)
        stored = report.data.main.stored
        if plan.step is StartupStepEnum.READY and stored is not None:
            return self._open(path, stored)
        return plan

    def create_at(self, path: Path, language: LanguageEnum) -> DataResult[StartupPlan]:
        """Create a new data file and open it.

        Args:
            path: Where to create it.
            language: UI language of the new settings.

        Returns:
            The ``READY`` plan, or the failure (``STORAGE_FILE_ALREADY_EXISTS``, write errors).
        """
        settings = self._defaults.new_settings(language)
        validation = UserSettingsRules.validate(settings)
        if validation.is_failure:
            return DataResult.fail(validation)
        created = self._file.create(path, self._defaults.initial(settings))
        if created.data is None:
            return DataResult.fail(created.validation)
        return DataResult.ok(self._open(path, created.data), created.validation)

    def restore(self, path: Path, source: RecoverySourceEnum) -> DataResult[StartupPlan]:
        """Replace the data file with a candidate and open it.

        Args:
            path: Data file path.
            source: Candidate.

        Returns:
            The ``READY`` plan, or the failure.
        """
        restored = self._file.restore(path, source)
        if restored.data is None:
            return DataResult.fail(restored.validation)
        return DataResult.ok(self._open(path, restored.data), restored.validation)

    def keep_current(self, path: Path) -> DataResult[StartupPlan]:
        """Put the newer ``.tmp`` aside (``.tmp.discarded-...``) and open the data file.

        Args:
            path: Data file path.

        Returns:
            The new plan (``READY`` normally), or the rename failure.
        """
        discarded = self._file.discard_temporary(path)
        if discarded.data is None:
            return DataResult.fail(discarded.validation)
        return DataResult.ok(self.inspect(path), discarded.validation)

    def start_empty(self, path: Path, language: LanguageEnum) -> DataResult[StartupPlan]:
        """Quarantine the damaged data file (if any) and create an empty one at the same path.

        Args:
            path: Data file path.
            language: UI language of the new settings.

        Returns:
            The ``READY`` plan, or the failure (the damaged file is never overwritten).
        """
        if self._file.exists(path):
            quarantined = self._file.quarantine(path)
            if quarantined.data is None:
                return DataResult.fail(quarantined.validation)
        return self.create_at(path, language)

    def _open(self, path: Path, stored: StoredUserData) -> StartupPlan:
        """Make a file the open one; sections it does not have yet are added and saved.

        Args:
            path: Data file path.
            stored: Its content.

        Returns:
            The ``READY`` plan.
        """
        self._session.reset(stored.data)
        self._coordinator.attach(path, stored.saved_at)
        self._defaults.complete_session(self._session)
        self._preferences.set_text(DATA_FILE_PATH_KEY, path.as_posix())
        _logger.info("Data file opened: %s", path)
        return StartupPlan(
            step=StartupStepEnum.READY,
            reason=StartupReasonEnum.OPENED,
            path=path,
            default_path=self._default_path,
            default_exists=self._file.exists(self._default_path),
        )
