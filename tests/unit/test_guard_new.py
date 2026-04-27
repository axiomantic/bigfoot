"""Tests for tripwire._guard -- new allow/deny/restrict context managers.

C9 added a check that `tripwire.allow/deny/restrict` raise outside any
active sandbox. The autouse `_set_active_verifier` fixture below sets
`_active_verifier` to a sentinel for each test in this module so that
the firewall stack mechanics can be exercised directly without standing
up a full sandbox.
"""

from collections.abc import Generator

import pytest

from tripwire._context import _active_verifier
from tripwire._firewall import Disposition, get_firewall_stack
from tripwire._firewall_request import HttpFirewallRequest, RedisFirewallRequest
from tripwire._guard import allow, deny, restrict
from tripwire._match import M


@pytest.fixture(autouse=True)
def _set_active_verifier() -> Generator[None, None, None]:
    """Satisfy C9 (`_active_verifier` must be set) without a real sandbox."""
    from tripwire._verifier import StrictVerifier

    StrictVerifier._suppress_direct_warning = True
    try:
        sentinel = StrictVerifier()
    finally:
        StrictVerifier._suppress_direct_warning = False
    token = _active_verifier.set(sentinel)
    try:
        yield
    finally:
        _active_verifier.reset(token)


class TestAllow:
    def test_allow_string_pushes_protocol_rule(self) -> None:
        with allow("http"):
            stack = get_firewall_stack()
            req = HttpFirewallRequest(host="example.com", port=80)
            assert stack.evaluate(req) == Disposition.ALLOW

    def test_allow_m_object(self) -> None:
        with allow(M(protocol="http", host="*.example.com")):
            stack = get_firewall_stack()
            req = HttpFirewallRequest(host="sub.example.com", port=80)
            assert stack.evaluate(req) == Disposition.ALLOW
            req_other = HttpFirewallRequest(host="other.com", port=80)
            assert stack.evaluate(req_other) == Disposition.DENY

    def test_allow_restores_stack(self) -> None:
        before = get_firewall_stack()
        with allow("http"):
            pass
        after = get_firewall_stack()
        assert len(before.frames) == len(after.frames)

    def test_allow_empty_raises(self) -> None:
        with pytest.raises(ValueError, match="at least one rule"):
            with allow():
                pass


class TestDeny:
    def test_deny_overrides_outer_allow(self) -> None:
        with allow("redis"):
            with deny(M(protocol="redis", command="FLUSHALL")):
                stack = get_firewall_stack()
                req_flush = RedisFirewallRequest(host="localhost", port=6379, command="FLUSHALL")
                assert stack.evaluate(req_flush) == Disposition.DENY
                req_get = RedisFirewallRequest(host="localhost", port=6379, command="GET")
                assert stack.evaluate(req_get) == Disposition.ALLOW


class TestRestrict:
    def test_restrict_blocks_other_protocols(self) -> None:
        with restrict(M(protocol="http")):
            with allow("redis"):
                stack = get_firewall_stack()
                req = RedisFirewallRequest(host="localhost", port=6379)
                # restrict(http) blocks redis even with inner allow
                assert stack.evaluate(req) == Disposition.DENY

    def test_restrict_allows_matching_protocol(self) -> None:
        with restrict(M(protocol="http")):
            with allow(M(protocol="http", host="*.example.com")):
                stack = get_firewall_stack()
                req = HttpFirewallRequest(host="sub.example.com", port=80)
                assert stack.evaluate(req) == Disposition.ALLOW

    def test_restrict_multiple_protocols_or(self) -> None:
        with restrict("http", "dns"):
            with allow("http", "dns"):
                stack = get_firewall_stack()
                http_req = HttpFirewallRequest(host="example.com", port=80)
                assert stack.evaluate(http_req) == Disposition.ALLOW
                redis_req = RedisFirewallRequest(host="localhost", port=6379)
                assert stack.evaluate(redis_req) == Disposition.DENY
