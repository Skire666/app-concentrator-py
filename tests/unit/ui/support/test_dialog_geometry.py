import pytest

from concentrator.ui.support.dialog_geometry import Box, clamped

HOST = Box(x=100, y=50, width=800, height=600)


@pytest.mark.parametrize(
    ("dialog", "expected"),
    [
        (Box(x=300, y=200, width=200, height=100), Box(x=300, y=200, width=200, height=100)),
        (Box(x=-500, y=200, width=200, height=100), Box(x=100, y=200, width=200, height=100)),
        (Box(x=850, y=200, width=200, height=100), Box(x=700, y=200, width=200, height=100)),
        (Box(x=300, y=-20, width=200, height=100), Box(x=300, y=50, width=200, height=100)),
        (Box(x=300, y=900, width=200, height=100), Box(x=300, y=550, width=200, height=100)),
        (Box(x=2000, y=2000, width=200, height=100), Box(x=700, y=550, width=200, height=100)),
        (Box(x=100, y=50, width=800, height=600), Box(x=100, y=50, width=800, height=600)),
    ],
)
def test_clamped_moves_the_dialog_the_least_to_stay_inside(dialog: Box, expected: Box) -> None:
    assert clamped(dialog, HOST) == expected


def test_clamped_centers_a_dialog_larger_than_the_window_along_that_axis() -> None:
    wide = Box(x=-300, y=900, width=1000, height=100)

    assert clamped(wide, HOST) == Box(x=0, y=550, width=1000, height=100)
    assert clamped(Box(x=0, y=0, width=1000, height=700), HOST) == Box(x=0, y=0, width=1000, height=700)
