from dataclasses import replace

import pytest

from concentrator.application.common.event_bus import EventBus
from concentrator.application.storage.storage_events import UserDataChangedEvent
from concentrator.domain.common.error_code_enum import ErrorCodeEnum
from concentrator.domain.settings.language_enum import LanguageEnum
from concentrator.domain.settings.user_settings import UserSettingsId
from concentrator.infrastructure.persistence.store_user_settings import StoreUserSettingsReader, StoreUserSettingsWriter
from concentrator.infrastructure.persistence.user_data_store import UserDataStore
from tests.fakes.recording_error_reporter import RecordingErrorReporter
from tests.fakes.user_data_factory import make_settings, make_user_data


class Setup:
    def __init__(self) -> None:
        bus = EventBus(RecordingErrorReporter())
        self.events: list[UserDataChangedEvent] = []
        bus.subscribe(UserDataChangedEvent, self.events.append)
        self.store = UserDataStore(bus)


@pytest.fixture
def setup() -> Setup:
    return Setup()


def test_store_without_file_refuses_access(setup: Setup) -> None:
    assert not setup.store.is_open
    with pytest.raises(RuntimeError, match="no data file"):
        setup.store.current()
    with pytest.raises(RuntimeError, match="no data file"):
        setup.store.apply(make_user_data())


def test_reset_opens_the_data_without_change_event(setup: Setup) -> None:
    setup.store.reset(make_user_data())

    assert setup.store.is_open
    assert setup.store.current() == make_user_data()
    assert setup.store.revision() == 1
    assert setup.events == []


def test_apply_changes_the_revision_and_publishes(setup: Setup) -> None:
    setup.store.reset(make_user_data(LanguageEnum.ENGLISH))

    revision = setup.store.apply(make_user_data(LanguageEnum.FRENCH))

    assert revision == 2
    assert setup.store.current() == make_user_data(LanguageEnum.FRENCH)
    assert setup.events == [UserDataChangedEvent(revision=2)]


def test_apply_of_equal_data_is_not_a_change(setup: Setup) -> None:
    setup.store.reset(make_user_data())

    assert setup.store.apply(make_user_data()) == 1
    assert setup.events == []


def test_settings_reader_and_writer(setup: Setup) -> None:
    setup.store.reset(make_user_data(LanguageEnum.ENGLISH))
    reader = StoreUserSettingsReader(setup.store)
    writer = StoreUserSettingsWriter(setup.store)

    updated = writer.update(make_settings(LanguageEnum.FRENCH))

    assert updated.data == make_settings(LanguageEnum.FRENCH)
    assert reader.read().data == make_settings(LanguageEnum.FRENCH)
    assert len(setup.events) == 1


def test_settings_writer_refuses_other_settings(setup: Setup) -> None:
    setup.store.reset(make_user_data())
    other = replace(make_settings(), id=UserSettingsId("other"))

    result = StoreUserSettingsWriter(setup.store).update(other)

    assert result.validation.error_codes == (ErrorCodeEnum.ENTITY_NOT_FOUND,)
    assert setup.events == []
