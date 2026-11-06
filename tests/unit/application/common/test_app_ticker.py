from concentrator.application.common.app_ticker import AppTicker


def test_tick_without_handler_does_nothing() -> None:
    AppTicker().tick()


def test_tick_calls_every_handler_once_in_order() -> None:
    ticker = AppTicker()
    calls: list[str] = []
    ticker.register(lambda: calls.append("timer"))
    ticker.register(lambda: calls.append("chime"))

    ticker.tick()
    ticker.tick()

    assert calls == ["timer", "chime", "timer", "chime"]
