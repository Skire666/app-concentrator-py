"""Time-ordered entity ids."""

import uuid
from typing import override

from concentrator.application.ports.id_generator_port import IdGeneratorPort


class Uuid7IdGenerator(IdGeneratorPort):
    """UUIDv7 ids (``uuid.uuid7``, Python 3.14): unique and sortable by creation time."""

    @override
    def new_id(self) -> str:
        return str(uuid.uuid7())
