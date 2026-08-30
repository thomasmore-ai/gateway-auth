# thomasmore-gateway-auth

Shared **trusted-header auth contract** for services behind
`thomasmore-ai/auth-gateway`. One source of truth for the wire protocol
so the producer (auth-gateway) and every consumer (catalog, connector,
whatever comes next) cannot drift.

## Why

Before this package, `auth-gateway` held the contract in `app/contract/`
and `thomasmore-ai/backend` held a hand-ported copy in
`apps/api/auth/contract.py`. Two independently-maintained copies of the
same header names and parsing logic is exactly the kind of drift this
package exists to make structurally impossible — see
`TZ-auth-gateway.md` §6 in `thomasmore.ai_website` for the original
design rationale, and `ThomasMoreAI/tm-gateway-auth` (a different,
unrelated org) for the pattern this was modeled on.

## Wire contract

auth-gateway injects, after validating a ZITADEL session:

| Header | Meaning |
|---|---|
| `X-Auth-User-Id` | ZITADEL subject (opaque string — not format-validated) |
| `X-Auth-Email` | user email |
| `X-Auth-Roles` | comma-separated role list (v1: only `user`) |
| `X-Auth-Auth-Kind` | `bearer` or `web-session` |
| `X-Auth-Contract-Version` | wire contract version the producer used |
| `X-Internal-Secret` | service-trust secret (not parsed by this package — see below) |

No `X-Auth-User-Id` ⇒ anonymous request. This package does not itself
validate `X-Internal-Secret` or IP allowlists — that's `auth-gateway`'s
own `app/internal_trust/` module (FastAPI-specific glue), kept out of
this package deliberately: this package is framework-agnostic (no
FastAPI or Django import), so it works unmodified as the consumer-side
contract in a Django/DRF service or a future FastAPI connector alike.

## Install

```toml
# pyproject.toml of a consumer
dependencies = [
    "thomasmore-gateway-auth @ git+https://github.com/thomasmore-ai/gateway-auth@v0.1.0",
]
```

## Use — consumer (parse)

```python
from thomasmore_gateway_auth import AuthContext, parse_auth_context

ctx = parse_auth_context(request.headers)  # any Mapping[str, str]
if ctx.is_authenticated:
    ...
```

Works against Django's `request.headers` (a `Mapping`) and FastAPI's
`request.headers` alike — no framework-specific adapter needed for
parsing. FastAPI-specific dependency wiring (`require_internal_trusted`
gate, `get_auth_context`) lives in `auth-gateway`'s own
`app/internal_trust/fastapi.py`, not here — this package only ships the
`Mapping` in / `Mapping` out functions.

## Use — producer (auth-gateway)

```python
from thomasmore_gateway_auth import AuthContext, inject_trusted_headers

inject_trusted_headers(response.headers, AuthContext(user_id=..., roles=("user",), auth_kind="web-session"))
```

`inject_trusted_headers` strips any caller-supplied `X-Auth-*` first — a
downstream service must never be able to forge its own identity by
setting the header itself; only the producer is allowed to set these.
It uses `del`/`in` rather than `.pop()`, so it also works against
Starlette's `Response.headers` (`MutableHeaders`), which implements the
mapping protocol but not `dict.pop()`.

## Versioning & compatibility

Two version numbers, on purpose:

- **`__version__`** — the package release. Bumps on every change (docs,
  refactor, bugfix).
- **`CONTRACT_VERSION`** — the *wire* version. Bumps ONLY when the
  headers change (new/renamed/removed header, or a change in how a
  value is serialized).

**Compatibility rule:** a producer and a consumer interoperate iff they
share the same compatibility **epoch** — not necessarily the exact same
`CONTRACT_VERSION`. An **additive** bump (a new header older consumers
ignore, newer consumers default when absent) keeps the epoch; only a
**breaking** change (a header renamed/removed, or serialization changed)
opens a new epoch. `is_contract_compatible(producer_version,
consumer_version)` encodes this rule.

How compatibility is tested:

- `parse(inject(ctx)) == ctx` round-trip (`tests/test_contract.py`).
- **Golden wire fixture** — the current parser must still read a frozen
  v1 sample, so an accidental breaking change fails CI here instead of
  silently 401-ing prod after a deploy.

## Develop

```bash
pip install -e ".[test]"
pytest
ruff check .
```
