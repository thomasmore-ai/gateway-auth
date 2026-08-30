"""Wire contract — the ``X-Auth-*`` / ``X-Internal-Secret`` header names.

Import these constants on both the producer (auth-gateway) and every
consumer side instead of hand-typing header strings — this is the whole
point of having a shared contract package: it makes the class of bug
where one side renames a header and the other doesn't structurally
impossible.
"""

from typing import Final


class Headers:
    USER_ID: Final[str] = "X-Auth-User-Id"
    EMAIL: Final[str] = "X-Auth-Email"
    ROLES: Final[str] = "X-Auth-Roles"
    AUTH_KIND: Final[str] = "X-Auth-Auth-Kind"
    CONTRACT_VERSION: Final[str] = "X-Auth-Contract-Version"
    INTERNAL_SECRET: Final[str] = "X-Internal-Secret"
    FORWARDED_FOR: Final[str] = "X-Forwarded-For"


ROLES_SEPARATOR = ","
