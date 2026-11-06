"""Error codes carried by validation issues.

Ranges: ``1xxx`` common validation, ``2xxx`` storage, ``3xxx`` config and i18n, ``4xxx`` timer,
``5xxx`` todo, ``6xxx`` focus, ``7xxx`` system. Every code has the UI message key
``error.<name_lowercase>`` in both catalogs.
"""

from typing import Final

from concentrator.domain.common.base_int_enum import BaseIntEnum
from concentrator.domain.common.error_category_enum import ErrorCategoryEnum

_CATEGORY_RANGE_SIZE: Final = 1000


class ErrorCodeEnum(BaseIntEnum):
    """Every expected failure of the application. Values are never renumbered or reused."""

    UNKNOWN = -1
    UNSET = 0

    # 1xxx common validation
    REQUIRED_VALUE_MISSING = 1001
    VALUE_OUT_OF_RANGE = 1002
    TEXT_TOO_LONG = 1003
    FORMAT_INVALID = 1004
    ENTITY_NOT_FOUND = 1005
    ENTITY_DUPLICATE_ID = 1006
    ENUM_VALUE_UNSET = 1007
    ENUM_VALUE_UNKNOWN = 1008
    DATETIME_NOT_UTC = 1009

    # 3xxx configuration
    CONFIG_FILE_NOT_FOUND = 3001
    CONFIG_SYNTAX_INVALID = 3002
    CONFIG_KEY_MISSING = 3003
    CONFIG_VALUE_INVALID = 3004
    CONFIG_KEY_UNEXPECTED = 3005

    # 31xx i18n catalogs
    CATALOG_FILE_NOT_FOUND = 3101
    CATALOG_SYNTAX_INVALID = 3102
    CATALOG_KEY_MISSING = 3103

    # 72xx process and Windows shell
    INSTANCE_LOCK_FAILED = 7201
    INSTANCE_SERVER_FAILED = 7202
    APP_USER_MODEL_ID_FAILED = 7203

    @property
    def category(self) -> ErrorCategoryEnum:
        """Category derived from the thousands digit (``UNKNOWN``/``UNSET`` map to the same members)."""
        return ErrorCategoryEnum.parse(self.value // _CATEGORY_RANGE_SIZE)
