from collections.abc import MutableMapping

from thomasmore_gateway_auth import CONTRACT_VERSION, AuthContext, Headers, inject_trusted_headers, parse_auth_context
from thomasmore_gateway_auth.version import is_contract_compatible


def test_roundtrip_authenticated():
    ctx = AuthContext(user_id="364403638170288132", email="a@b.com", roles=("user",), auth_kind="web-session")
    headers: dict[str, str] = {}
    inject_trusted_headers(headers, ctx)
    assert parse_auth_context(headers) == ctx


def test_roundtrip_anonymous():
    ctx = AuthContext()
    headers: dict[str, str] = {}
    inject_trusted_headers(headers, ctx)
    assert Headers.USER_ID not in headers
    assert parse_auth_context(headers) == ctx


def test_inject_strips_caller_supplied_headers():
    headers = {Headers.USER_ID: "forged", Headers.ROLES: "admin"}
    inject_trusted_headers(headers, AuthContext(user_id="real", roles=("user",)))
    assert headers[Headers.USER_ID] == "real"
    assert headers[Headers.ROLES] == "user"


def test_inject_sets_contract_version():
    headers: dict[str, str] = {}
    inject_trusted_headers(headers, AuthContext(user_id="u1"))
    assert headers[Headers.CONTRACT_VERSION] == CONTRACT_VERSION


def test_multiple_roles_serialize_and_parse():
    ctx = AuthContext(user_id="u1", roles=("user", "admin"))
    headers: dict[str, str] = {}
    inject_trusted_headers(headers, ctx)
    assert headers[Headers.ROLES] == "user,admin"
    assert parse_auth_context(headers).roles == ("user", "admin")


class _NoPopMutableMapping(MutableMapping):
    """Minimal stand-in for Starlette's ``MutableHeaders``: implements the
    mapping protocol but deliberately has no ``.pop()`` — regression guard
    for a real bug found in auth-gateway, where ``inject_trusted_headers``
    called ``.pop(name, None)`` and broke against ``Response.headers`` in
    a real FastAPI route. Kept dependency-free here (no starlette import)
    since this package has no framework dependency."""

    def __init__(self):
        self._data: dict[str, str] = {}

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        del self._data[key]

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)


def test_inject_works_against_mapping_without_pop():
    headers = _NoPopMutableMapping()
    inject_trusted_headers(headers, AuthContext(user_id="u1", roles=("user",)))
    assert headers[Headers.USER_ID] == "u1"
    assert headers[Headers.ROLES] == "user"


def test_same_version_is_compatible():
    assert is_contract_compatible(CONTRACT_VERSION, CONTRACT_VERSION)


def test_golden_fixture_v1_still_parses():
    # A frozen sample of what a v1 producer actually sent on the wire.
    # If this test breaks, the change is a BREAKING contract change —
    # bump CONTRACT_VERSION and record it in version.py's
    # _BREAKING_VERSIONS, don't just fix the fixture.
    golden_headers = {
        Headers.USER_ID: "364403638170288132",
        Headers.EMAIL: "user@example.com",
        Headers.ROLES: "user",
        Headers.AUTH_KIND: "web-session",
        Headers.CONTRACT_VERSION: "1.0.0",
    }
    ctx = parse_auth_context(golden_headers)
    assert ctx.user_id == "364403638170288132"
    assert ctx.roles == ("user",)
    assert ctx.auth_kind == "web-session"
