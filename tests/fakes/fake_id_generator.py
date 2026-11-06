"""Predictable ids."""

from typing import override

from concentrator.application.ports.id_generator_port import IdGeneratorPort


class FakeIdGenerator(IdGeneratorPort):
    """Returns ``id-0001``, ``id-0002``, ..."""

    def __init__(self, prefix: str = "id") -> None:
        self._prefix = prefix
        self._count = 0

    @override
    def new_id(self) -> str:
        self._count += 1
        return f"{self._prefix}-{self._count:04d}"
