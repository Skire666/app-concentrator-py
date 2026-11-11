"""Values of the ``[focus]`` section used by the use cases, the read pipeline and the presentation."""

from dataclasses import dataclass
from typing import Self

from concentrator.application.common.app_config import FocusSection
from concentrator.domain.focus.focus_limits import FocusLimits


@dataclass(frozen=True, slots=True, kw_only=True)
class FocusDefaults:
    """Limits of the focus queue.

    Attributes:
        limits: Bounds applied by the domain rules.
        picker_max_results: Most tasks proposed by the search field of the queue.
    """

    limits: FocusLimits
    picker_max_results: int

    @classmethod
    def from_section(cls, section: FocusSection) -> Self:
        """Build the values from the ``[focus]`` section.

        Args:
            section: Loaded section.

        Returns:
            The defaults.
        """
        return cls(limits=FocusLimits(max_items=section.max_items), picker_max_results=section.picker_max_results)
