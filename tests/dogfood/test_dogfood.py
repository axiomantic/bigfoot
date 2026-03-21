"""Dogfood tests: bigfoot uses itself to test bigfoot.

These tests exercise bigfoot's own internals via bigfoot's MockPlugin and
HttpPlugin, validating production-style usage rather than isolated unit behavior.
"""

import sys
import types

import pytest
from dirty_equals import AnyThing, IsInstance

import bigfoot
from bigfoot import (
    MockPlugin,
    UnassertedInteractionsError,
    UnmockedInteractionError,
    UnusedMocksError,
)
from bigfoot._mock_plugin import ImportSiteMock

pytestmark = pytest.mark.integration


def _create_fake_module(name: str, **attrs: object) -> types.ModuleType:
    mod = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


# ---------------------------------------------------------------------------
# 1. MockPlugin records and asserts a collaborator interaction
# ---------------------------------------------------------------------------


def test_mock_plugin_records_and_asserts_collaborator_interaction() -> None:
    """Use bigfoot.mock() to mock a module-level function, verify interaction recorded."""
    mod = _create_fake_module("_df_payment", charge=lambda *a, **kw: None)
    try:
        service_mock = bigfoot.mock("_df_payment:charge")
        service_mock.returns({"status": "ok", "id": "ch_001"})

        with bigfoot.sandbox():
            result = mod.charge("order_99", amount=500)

        assert result == {"status": "ok", "id": "ch_001"}
        service_mock.assert_call(
            args=("order_99",),
            kwargs={"amount": 500},
        )
    finally:
        del sys.modules["_df_payment"]


# ---------------------------------------------------------------------------
# 2. Multiple mock calls asserted in FIFO order
# ---------------------------------------------------------------------------


def test_multiple_calls_asserted_in_fifo_order() -> None:
    """Multiple side effects consumed in FIFO order, each interaction asserted."""
    mod = _create_fake_module("_df_counter", tick=lambda: None)
    try:
        counter_mock = bigfoot.mock("_df_counter:tick")
        counter_mock.returns(1).returns(2).returns(3)

        with bigfoot.sandbox():
            first = mod.tick()
            second = mod.tick()
            third = mod.tick()

        assert first == 1
        assert second == 2
        assert third == 3
        counter_mock.assert_call(args=(), kwargs={})
        counter_mock.assert_call(args=(), kwargs={})
        counter_mock.assert_call(args=(), kwargs={})
    finally:
        del sys.modules["_df_counter"]


# ---------------------------------------------------------------------------
# 3. UnmockedInteractionError exact message content
# ---------------------------------------------------------------------------


def test_unmocked_interaction_error_exact_message() -> None:
    """UnmockedInteractionError includes source_id, args, kwargs."""

    class _DataStore:
        @staticmethod
        def fetch(key: str) -> str:
            return f"real_{key}"

    store = _DataStore()
    mock = bigfoot.mock.object(store, "fetch")

    with bigfoot.sandbox():
        with pytest.raises(UnmockedInteractionError) as exc_info:
            store.fetch("user_id_123")

    err = exc_info.value
    assert "fetch" in err.source_id
    assert err.args_tuple == ("user_id_123",)
    assert err.kwargs == {}


# ---------------------------------------------------------------------------
# 4. UnassertedInteractionsError at teardown
# ---------------------------------------------------------------------------


def test_unasserted_interactions_error_at_teardown() -> None:
    """verify_all() raises UnassertedInteractionsError when interaction is not asserted."""
    mod = _create_fake_module("_df_logger", log=lambda *a: None)
    try:
        log_mock = bigfoot.mock("_df_logger:log")
        log_mock.returns(None)

        with bigfoot.sandbox():
            mod.log("event_happened")
            # Deliberately skip assert

        with pytest.raises(UnassertedInteractionsError) as exc_info:
            bigfoot.verify_all()

        err = exc_info.value
        assert len(err.interactions) == 1
        assert "log" in err.interactions[0].source_id
        assert err.interactions[0].sequence == 0

        # Assert the interaction so the auto-verifier teardown does not raise again
        log_mock.assert_call(args=("event_happened",), kwargs={})
    finally:
        del sys.modules["_df_logger"]


# ---------------------------------------------------------------------------
# 5. UnusedMocksError at teardown
# ---------------------------------------------------------------------------


def test_unused_mocks_error_at_teardown() -> None:
    """verify_all() raises UnusedMocksError when a required mock is never called."""
    mod = _create_fake_module("_df_emailer", send_email=lambda *a: None)
    try:
        email_mock = bigfoot.mock("_df_emailer:send_email")
        email_mock.returns(True)

        with bigfoot.sandbox():
            pass  # Never call send_email

        with pytest.raises(UnusedMocksError) as exc_info:
            bigfoot.verify_all()

        err = exc_info.value
        assert len(err.mocks) == 1
        assert "send_email" in err.mocks[0].method_name or "_df_emailer" in err.mocks[0].mock_name

        # hint contains dynamic registration traceback; verify structure
        assert err.hint.startswith("1 mock(s) were registered but never triggered\n")
        assert "Mock registered at:" in err.hint
        assert "Remove this mock if it's not needed" in err.hint

        assert str(err) == err.hint

        # Mark the mock as not required so the auto-verifier teardown does not raise
        verifier = bigfoot.current_verifier()
        for plugin in verifier._plugins:
            if isinstance(plugin, MockPlugin):
                for mock_obj in plugin._mocks:
                    for method_proxy in mock_obj._methods.values():
                        for config in method_proxy._config_queue:
                            config.required = False
    finally:
        del sys.modules["_df_emailer"]


# ---------------------------------------------------------------------------
# 6. required(False) suppresses UnusedMocksError
# ---------------------------------------------------------------------------


def test_required_false_suppresses_unused_mocks_error() -> None:
    """Mocks registered with required=False do not cause UnusedMocksError."""

    class _Cache:
        @staticmethod
        def get(key: str) -> str:
            return f"cached_{key}"

    cache = _Cache()
    mock = bigfoot.mock.object(cache, "get")
    # Access __call__ to configure, mark not required
    mock.__getattr__("__call__").required(False).returns(None)

    with bigfoot.sandbox():
        pass  # Never call get

    # verify_all() is called automatically at teardown by _bigfoot_auto_verifier -- must not raise


# ---------------------------------------------------------------------------
# 7. .raises() side effect is recorded and must be asserted
# ---------------------------------------------------------------------------


def test_raises_side_effect_is_recorded_and_assertable() -> None:
    """Interaction from .raises() is recorded in the timeline and must be asserted."""
    mod = _create_fake_module("_df_database", connect=lambda: None)
    try:
        exc = ConnectionError("db down")
        db_mock = bigfoot.mock("_df_database:connect")
        db_mock.raises(exc)

        with bigfoot.sandbox():
            with pytest.raises(ConnectionError, match="db down"):
                mod.connect()

        db_mock.assert_call(
            args=(),
            kwargs={},
            raised=exc,
        )
    finally:
        del sys.modules["_df_database"]


# ---------------------------------------------------------------------------
# 8. .calls() side effect delegates to fn and is recorded
# ---------------------------------------------------------------------------


def test_calls_side_effect_delegates_to_fn() -> None:
    """Interaction from .calls() invokes the function with forwarded args."""
    mod = _create_fake_module("_df_calc", add=lambda x, y: x + y)
    try:
        calc_mock = bigfoot.mock("_df_calc:add")
        calc_mock.calls(lambda x, y: x + y)

        with bigfoot.sandbox():
            result = mod.add(3, 4)

        assert result == 7
        calc_mock.assert_call(
            args=(3, 4),
            kwargs={},
        )
    finally:
        del sys.modules["_df_calc"]


# ---------------------------------------------------------------------------
# 9. in_any_order allows assertions regardless of call order
# ---------------------------------------------------------------------------


def test_in_any_order_allows_out_of_order_assertions() -> None:
    """in_any_order() allows assertions in any sequence across two mocks."""
    mod = _create_fake_module(
        "_df_notify",
        send_email=lambda *a: None,
        send_sms=lambda *a: None,
    )
    try:
        email_mock = bigfoot.mock("_df_notify:send_email")
        sms_mock = bigfoot.mock("_df_notify:send_sms")
        email_mock.returns(True)
        sms_mock.returns(True)

        with bigfoot.sandbox():
            mod.send_sms("hello")
            mod.send_email("world")

        # Assert out-of-order: email first, then sms
        with bigfoot.in_any_order():
            email_mock.assert_call(args=("world",), kwargs={})
            sms_mock.assert_call(args=("hello",), kwargs={})
    finally:
        del sys.modules["_df_notify"]


# ---------------------------------------------------------------------------
# 10. bigfoot.mock() lazily creates MockPlugin
# ---------------------------------------------------------------------------


def test_verifier_mock_lazily_creates_mock_plugin() -> None:
    """bigfoot.mock() creates MockPlugin on first call without explicit instantiation."""
    verifier = bigfoot.current_verifier()

    # Before any mock() call, no MockPlugin registered (but auto-instantiated plugins are)
    assert not any(isinstance(p, MockPlugin) for p in verifier._plugins)
    initial_count = len(verifier._plugins)

    mock = bigfoot.mock("os.path:sep")

    # After mock(), MockPlugin is registered alongside auto-instantiated plugins
    assert len(verifier._plugins) == initial_count + 1
    assert any(isinstance(p, MockPlugin) for p in verifier._plugins)
    assert isinstance(mock, ImportSiteMock)


# ---------------------------------------------------------------------------
# 11. mock() returns different objects for different paths
# ---------------------------------------------------------------------------


def test_mock_returns_different_instances_for_different_paths() -> None:
    """bigfoot.mock() with different paths returns different objects."""
    mock_a = bigfoot.mock("os.path:sep")
    mock_b = bigfoot.mock("os.path:join")

    assert mock_a is not mock_b


# ---------------------------------------------------------------------------
# 12. Async context: MockPlugin works inside an async test
# ---------------------------------------------------------------------------


async def test_mock_plugin_works_in_async_context() -> None:
    """bigfoot MockPlugin correctly records interactions inside an async test."""
    mod = _create_fake_module("_df_async_svc", fetch_data=lambda *a: None)
    try:
        mock = bigfoot.mock("_df_async_svc:fetch_data")
        mock.returns({"value": 42})

        async with bigfoot.sandbox():
            result = mod.fetch_data("key")

        assert result == {"value": 42}
        mock.assert_call(
            args=("key",),
            kwargs={},
        )
    finally:
        del sys.modules["_df_async_svc"]


# ---------------------------------------------------------------------------
# 13. HttpPlugin: full cycle with httpx (skip if not installed)
# ---------------------------------------------------------------------------


def test_http_plugin_full_cycle_httpx() -> None:
    """Full mock + assert + verify cycle using httpx GET."""
    httpx = pytest.importorskip("httpx")

    bigfoot.http.mock_response(
        "GET",
        "https://api.stripe.com/v1/charges",
        json={"id": "ch_123", "amount": 5000},
        status=200,
    )

    with bigfoot.sandbox():
        response = httpx.get("https://api.stripe.com/v1/charges")

    assert response.status_code == 200
    assert response.json() == {"id": "ch_123", "amount": 5000}
    bigfoot.assert_interaction(
        bigfoot.http.request,
        method="GET",
        url="https://api.stripe.com/v1/charges",
        request_headers=AnyThing(),
        request_body="",
        status=200,
        response_headers=AnyThing(),
        response_body=AnyThing(),
    )


# ---------------------------------------------------------------------------
# 14. MockPlugin and HttpPlugin together: global FIFO order
# ---------------------------------------------------------------------------


def test_mock_and_http_plugins_tracked_in_global_fifo_order() -> None:
    """MockPlugin and HttpPlugin interactions share a global FIFO timeline."""
    httpx = pytest.importorskip("httpx")

    mod = _create_fake_module("_df_auth", authenticate=lambda *a: None)
    try:
        auth_mock = bigfoot.mock("_df_auth:authenticate")
        auth_mock.returns({"token": "tok_abc"})

        bigfoot.http.mock_response(
            "POST",
            "https://api.example.com/data",
            json={"created": True},
            status=201,
        )

        with bigfoot.sandbox():
            auth_result = mod.authenticate("user_x")
            http_response = httpx.post("https://api.example.com/data", json={})

        assert auth_result == {"token": "tok_abc"}
        assert http_response.status_code == 201
        # Assert in the same FIFO order they were called
        auth_mock.assert_call(
            args=("user_x",),
            kwargs={},
        )
        bigfoot.assert_interaction(
            bigfoot.http.request,
            method="POST",
            url="https://api.example.com/data",
            request_headers=AnyThing(),
            request_body=AnyThing(),
            status=201,
            response_headers=AnyThing(),
            response_body=AnyThing(),
        )
    finally:
        del sys.modules["_df_auth"]


# ---------------------------------------------------------------------------
# 15. spy() records interaction and delegates to real object
# ---------------------------------------------------------------------------


def test_spy_records_and_delegates() -> None:
    """bigfoot.spy() creates a spy that delegates to real implementation."""

    class _Calculator:
        @staticmethod
        def add(x: int, y: int) -> int:
            return x + y

    mod = _create_fake_module("_df_calc_spy", add=_Calculator.add)
    try:
        calc_spy = bigfoot.spy("_df_calc_spy:add")

        with bigfoot.sandbox():
            result = mod.add(10, 20)

        assert result == 30
        calc_spy.assert_call(args=(10, 20), kwargs={}, returned=30)
    finally:
        del sys.modules["_df_calc_spy"]


# ---------------------------------------------------------------------------
# 16. spy() with real method that raises: interaction recorded, exception propagated
# ---------------------------------------------------------------------------


def test_spy_records_when_real_raises() -> None:
    """spy(): if real method raises, interaction is still recorded and exception re-raised."""

    def _flaky_fetch() -> None:
        raise ConnectionError("unreachable")

    mod = _create_fake_module("_df_flaky_spy", fetch=_flaky_fetch)
    try:
        flaky_spy = bigfoot.spy("_df_flaky_spy:fetch")

        with bigfoot.sandbox():
            with pytest.raises(ConnectionError, match="unreachable"):
                mod.fetch()

        flaky_spy.assert_call(
            args=(), kwargs={}, raised=IsInstance(ConnectionError)
        )
    finally:
        del sys.modules["_df_flaky_spy"]


# ---------------------------------------------------------------------------
# 17. MissingAssertionFieldsError raised when assertable field omitted
# ---------------------------------------------------------------------------


def test_missing_assertion_fields_error_raised_for_mock() -> None:
    """assert_interaction() raises MissingAssertionFieldsError when args/kwargs omitted."""
    from bigfoot import MissingAssertionFieldsError

    mod = _create_fake_module("_df_svc_fields", process=lambda *a: None)
    try:
        mock = bigfoot.mock("_df_svc_fields:process")
        mock.returns("done")

        with bigfoot.sandbox():
            mod.process("input")

        # Use assert_interaction directly with no fields to trigger MissingAssertionFieldsError
        method_proxy = mock.__getattr__("__call__")
        with pytest.raises(MissingAssertionFieldsError) as exc_info:
            bigfoot.assert_interaction(method_proxy)  # missing args and kwargs

        assert "args" in exc_info.value.missing_fields
        assert "kwargs" in exc_info.value.missing_fields

        # Now assert correctly so teardown doesn't raise
        mock.assert_call(args=("input",), kwargs={})
    finally:
        del sys.modules["_df_svc_fields"]


# ---------------------------------------------------------------------------
# 18. HTTP pass_through routes request to real backend (mocked at transport level)
# ---------------------------------------------------------------------------


def test_http_pass_through_routes_to_real_backend() -> None:
    """pass_through() routes the matched request to the real transport and records interaction."""
    httpx = pytest.importorskip("httpx")
    from bigfoot.plugins.http import HttpPlugin

    bigfoot.http.pass_through("GET", "https://real-api.example.com/data")

    fake_response = httpx.Response(200, json={"real": True})

    with bigfoot.sandbox():
        real_original = HttpPlugin._original_httpx_transport_handle
        HttpPlugin._original_httpx_transport_handle = lambda transport_self, request: fake_response  # type: ignore[assignment]
        try:
            response = httpx.get("https://real-api.example.com/data")
        finally:
            HttpPlugin._original_httpx_transport_handle = real_original  # type: ignore[assignment]

    assert response.status_code == 200
    bigfoot.assert_interaction(
        bigfoot.http.request,
        method="GET",
        url="https://real-api.example.com/data",
        request_headers=AnyThing(),
        request_body="",
        status=200,
        response_headers=AnyThing(),
        response_body=AnyThing(),
    )
