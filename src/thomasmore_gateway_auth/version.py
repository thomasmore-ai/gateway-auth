"""Two version numbers on purpose (TZ-auth-gateway.md §5.1):

- ``__version__`` — this package's release. Bumps on every change (docs,
  refactor, bugfix).
- ``CONTRACT_VERSION`` — the *wire* version. Bumps ONLY when the
  ``X-Auth-*`` headers themselves change (new/renamed/removed header, or a
  change in how a value is serialized).

Compatibility rule: two sides (auth-gateway and a consumer) interoperate
iff they share the same compatibility *epoch* — not necessarily the exact
same ``CONTRACT_VERSION``. An additive bump (a new header older consumers
ignore, newer consumers default when absent) keeps the epoch; only a
breaking change (a header renamed/removed, or serialization changed)
opens a new epoch.
"""

__version__ = "0.1.0"

CONTRACT_VERSION = "1.0.0"

# Populate with CONTRACT_VERSION strings that introduced a breaking change
# (renamed/removed header, changed serialization). Empty until the first
# breaking change ever ships.
_BREAKING_VERSIONS: tuple[str, ...] = ("1.0.0",)


def _epoch(contract_version: str) -> str:
    """The compatibility epoch a given CONTRACT_VERSION belongs to — the
    most recent breaking version at or before it."""
    candidates = [v for v in _BREAKING_VERSIONS if _version_tuple(v) <= _version_tuple(contract_version)]
    return max(candidates, key=_version_tuple) if candidates else contract_version


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(p) for p in v.split("."))


def is_contract_compatible(producer_version: str, consumer_version: str) -> bool:
    """True iff producer and consumer share the same compatibility epoch."""
    return _epoch(producer_version) == _epoch(consumer_version)
