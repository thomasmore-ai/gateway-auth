"""``AuthContext`` — the parsed, in-process representation of an identity
resolved by auth-gateway, plus the producer/consumer functions that
serialize it to/from ``X-Auth-*`` headers.

No ``X-Auth-User-Id`` on the incoming request means an anonymous request
— callers decide for themselves whether that's acceptable (a public
catalog endpoint stays public; a vote endpoint would reject it).

Framework-agnostic on purpose: this module has no dependency on FastAPI,
Django, or any other web framework, so it works unmodified as the
consumer-side contract in a Django/DRF service (``request.headers`` is a
``Mapping[str, str]``) just as well as a FastAPI one (``Response.headers``
is a ``MutableMapping[str, str]``, just not one that supports ``.pop()``
— see the ``inject_trusted_headers`` implementation note below).
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass, field
from typing import Literal

from thomasmore_gateway_auth.headers import ROLES_SEPARATOR, Headers
from thomasmore_gateway_auth.version import CONTRACT_VERSION

AuthKind = Literal["bearer", "web-session"]


@dataclass(frozen=True)
class AuthContext:
    user_id: str | None = None
    email: str | None = None
    roles: tuple[str, ...] = field(default_factory=tuple)
    auth_kind: AuthKind | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None

    def has_role(self, role: str) -> bool:
        return role in self.roles


ANONYMOUS = AuthContext()


def inject_trusted_headers(
    headers: MutableMapping[str, str],
    ctx: AuthContext,
    *,
    include_contract_version: bool = True,
) -> MutableMapping[str, str]:
    """Producer side: stamp ``ctx`` onto an outgoing header mapping.

    Strips any caller-supplied ``X-Auth-*`` first — a downstream service
    must never be able to forge its own identity by just setting the
    header itself; only auth-gateway is allowed to set these.

    Uses ``del``/``in`` rather than ``.pop(name, None)`` so this also
    works against Starlette's ``MutableHeaders`` (e.g. ``Response.headers``
    in a FastAPI route) — it implements the mapping protocol but not
    ``dict.pop``.
    """
    for name in (Headers.USER_ID, Headers.EMAIL, Headers.ROLES, Headers.AUTH_KIND):
        if name in headers:
            del headers[name]

    if ctx.user_id is not None:
        headers[Headers.USER_ID] = ctx.user_id
    if ctx.email is not None:
        headers[Headers.EMAIL] = ctx.email
    if ctx.roles:
        headers[Headers.ROLES] = ROLES_SEPARATOR.join(ctx.roles)
    if ctx.auth_kind is not None:
        headers[Headers.AUTH_KIND] = ctx.auth_kind
    if include_contract_version:
        headers[Headers.CONTRACT_VERSION] = CONTRACT_VERSION
    return headers


def parse_auth_context(headers: Mapping[str, str]) -> AuthContext:
    """Consumer side: read an ``AuthContext`` back out of inbound headers.

    ``X-Auth-User-Id`` is opaque — ZITADEL subjects are not guaranteed to
    be UUIDs, so this does not format-validate it. Absence of the header
    means an anonymous request, not an error.
    """
    user_id = headers.get(Headers.USER_ID) or None
    email = headers.get(Headers.EMAIL) or None
    roles_raw = headers.get(Headers.ROLES) or ""
    roles = tuple(r.strip() for r in roles_raw.split(ROLES_SEPARATOR) if r.strip())
    auth_kind = headers.get(Headers.AUTH_KIND) or None

    if user_id is None:
        return ANONYMOUS

    return AuthContext(
        user_id=user_id,
        email=email,
        roles=roles,
        auth_kind=auth_kind,  # type: ignore[arg-type]
    )
