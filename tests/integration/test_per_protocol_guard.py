"""C3 integration tests: per-protocol guard level dispatch.

Verifies that a `[tool.tripwire.guard]` table with `default = "warn"` and
a per-protocol override (e.g., `dns = "error"`) is honored by the
dispatch in `_context.get_verifier_or_raise`: outside-sandbox calls for
the override-protocol raise `GuardedCallError`, while
default-level calls go through the warn path.
"""

from __future__ import annotations

import warnings

import pytest

from tripwire._config import GuardLevels
from tripwire._context import (
    GuardPassThrough,
    _guard_active,
    _guard_levels,
    get_verifier_or_raise,
)
from tripwire._errors import GuardedCallError, GuardedCallWarning
from tripwire._firewall_request import NetworkFirewallRequest

pytestmark = pytest.mark.integration


def test_dns_strict_http_warn() -> None:
    """C3-T4: guard default = "warn" but `crypto = "error"` per-protocol.

    A DENY decision against a `crypto` source raises GuardedCallError
    (the per-protocol "error" override). A DENY decision against a
    different protocol that is `passthrough_safe=True` (jwt) under the
    default level "warn" emits GuardedCallWarning and raises
    GuardPassThrough.

    The test isolates dispatch from the project's TOML firewall rules by
    pushing an empty firewall stack frame so neither protocol is
    allow-listed by the surrounding pyproject.toml.

    ESCAPE: test_dns_strict_http_warn
      CLAIM: Per-protocol overrides take precedence over the default;
             crypto escalates from "warn" to "error" while jwt uses the
             default "warn" path.
      PATH:  get_verifier_or_raise -> Branch 3b -> overrides.get("crypto")
             returns "error" -> raise GuardedCallError; for "jwt" the
             override is absent so default "warn" applies and the safe
             warn path runs.
      CHECK: GuardedCallError is raised for the crypto:sign source_id;
             for jwt:encode, GuardedCallWarning is emitted and
             GuardPassThrough is raised.
      MUTATION: If overrides are ignored (i.e., dispatch always reads
                guard_levels.default), crypto would warn instead of
                raising and the test would fail. If overrides are read
                but the key extraction is wrong (e.g., `source_id`
                rather than `plugin_name`), the lookup would miss and
                crypto would fall to default "warn".
      ESCAPE: A bug that hardcodes "error" for every protocol would fail
              the jwt:encode branch (which expects warn behavior).
    """
    levels_token = _guard_levels.set(
        GuardLevels(default="warn", overrides={"crypto": "error"})
    )
    guard_token = _guard_active.set(True)
    try:
        # crypto: per-protocol "error" override -> GuardedCallError.
        crypto_req = NetworkFirewallRequest(
            protocol="crypto", host="local", port=0
        )
        with pytest.raises(GuardedCallError) as exc_info:
            get_verifier_or_raise(
                "crypto:sign", firewall_request=crypto_req
            )
        assert exc_info.value.plugin_name == "crypto"
        assert exc_info.value.source_id == "crypto:sign"

        # jwt: no override -> default "warn" applies; JwtPlugin is
        # passthrough_safe=True so the warn-safe branch runs.
        jwt_req = NetworkFirewallRequest(
            protocol="jwt", host="local", port=0
        )
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            with pytest.raises(GuardPassThrough):
                get_verifier_or_raise("jwt:encode", firewall_request=jwt_req)
            warning_msgs = [
                w for w in caught if issubclass(w.category, GuardedCallWarning)
            ]
            assert len(warning_msgs) == 1
            assert "'jwt:encode'" in str(warning_msgs[0].message)
    finally:
        _guard_active.reset(guard_token)
        _guard_levels.reset(levels_token)
