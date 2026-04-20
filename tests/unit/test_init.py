# tests/unit/test_init.py
"""Unit tests for bigfoot.__init__ public API.

Verifies that all public names are importable directly from the top-level
package and that __all__ contains exactly the expected names.
"""

import pytest


def test_all_contains_expected_names() -> None:
    """__all__ must be exactly the declared public API set."""
    # ESCAPE: if __all__ contained extras or was missing entries callers get
    # wrong autocomplete / wildcard-import results
    import bigfoot

    expected_all = {
        # Plugin authoring API
        "BasePlugin",
        "Interaction",
        "Timeline",
        "GuardPassThrough",
        "get_verifier_or_raise",
        "is_guard_eligible",
        "PluginEntry",
        # Classes
        "StrictVerifier",
        "SandboxContext",
        "InAnyOrderContext",
        "MockPlugin",
        "DatabasePlugin",
        "LoggingPlugin",
        "PopenPlugin",
        "SmtpPlugin",
        "SocketPlugin",
        "AsyncWebSocketPlugin",
        "SyncWebSocketPlugin",
        "RedisPlugin",
        "MongoPlugin",
        "CeleryPlugin",
        "DnsPlugin",
        "MemcachePlugin",
        "Psycopg2Plugin",
        "AsyncpgPlugin",
        "AsyncSubprocessPlugin",
        "Boto3Plugin",
        "ElasticsearchPlugin",
        "JwtPlugin",
        "CryptoPlugin",
        # Guard mode
        "allow",
        "deny",
        "restrict",
        "GuardedCallError",
        "GuardedCallWarning",
        # Firewall
        "Disposition",
        "FirewallRequest",
        # Match
        "M",
        # Errors
        "AllWildcardAssertionError",
        "BigfootConfigError",
        "BigfootError",
        "AssertionInsideSandboxError",
        "AutoAssertError",
        "InvalidStateError",
        "NoActiveVerifierError",
        "UnmockedInteractionError",
        "UnassertedInteractionsError",
        "UnusedMocksError",
        "VerificationError",
        "InteractionMismatchError",
        "SandboxNotActiveError",
        "ConflictError",
        "MissingAssertionFieldsError",
        # Module-level API
        "mock",
        "sandbox",
        "assert_interaction",
        "in_any_order",
        "verify_all",
        "current_verifier",
        "spy",
        "http",
        "subprocess",
        "popen",
        "smtp",
        "socket",
        "db",
        "async_websocket",
        "sync_websocket",
        "redis",
        "mongo",
        "dns",
        "memcache",
        "celery",
        "log",
        "async_subprocess",
        "psycopg2",
        "asyncpg",
        "boto3",
        "elasticsearch",
        "jwt",
        "crypto",
        "FileIoPlugin",
        "file_io",
        "PikaPlugin",
        "pika",
        "SshPlugin",
        "ssh",
        "GrpcPlugin",
        "grpc",
        "McpPlugin",
        "mcp",
        "NativePlugin",
        "native",
    }
    assert set(bigfoot.__all__) == expected_all


def test_assertion_inside_sandbox_error_importable() -> None:
    """AssertionInsideSandboxError must be importable from the top-level package."""
    from bigfoot import AssertionInsideSandboxError
    from bigfoot._errors import AssertionInsideSandboxError as _AssertionInsideSandboxError

    assert AssertionInsideSandboxError is _AssertionInsideSandboxError


def test_strict_verifier_importable() -> None:
    """StrictVerifier must be importable from the top-level package."""
    # ESCAPE: if the import was missing or aliased wrongly instantiation would fail
    from bigfoot import StrictVerifier
    from bigfoot._verifier import StrictVerifier as _StrictVerifier

    assert StrictVerifier is _StrictVerifier


def test_sandbox_context_importable() -> None:
    """SandboxContext must be importable from the top-level package."""
    from bigfoot import SandboxContext
    from bigfoot._verifier import SandboxContext as _SandboxContext

    assert SandboxContext is _SandboxContext


def test_in_any_order_context_importable() -> None:
    """InAnyOrderContext must be importable from the top-level package."""
    from bigfoot import InAnyOrderContext
    from bigfoot._verifier import InAnyOrderContext as _InAnyOrderContext

    assert InAnyOrderContext is _InAnyOrderContext


def test_mock_plugin_importable() -> None:
    """MockPlugin must be importable from the top-level package."""
    from bigfoot import MockPlugin
    from bigfoot._mock_plugin import MockPlugin as _MockPlugin

    assert MockPlugin is _MockPlugin


def test_bigfoot_error_importable() -> None:
    """BigfootError must be importable from the top-level package."""
    from bigfoot import BigfootError
    from bigfoot._errors import BigfootError as _BigfootError

    assert BigfootError is _BigfootError


def test_unmocked_interaction_error_importable() -> None:
    """UnmockedInteractionError must be importable from the top-level package."""
    from bigfoot import UnmockedInteractionError
    from bigfoot._errors import UnmockedInteractionError as _UnmockedInteractionError

    assert UnmockedInteractionError is _UnmockedInteractionError


def test_unasserted_interactions_error_importable() -> None:
    """UnassertedInteractionsError must be importable from the top-level package."""
    from bigfoot import UnassertedInteractionsError
    from bigfoot._errors import UnassertedInteractionsError as _UnassertedInteractionsError

    assert UnassertedInteractionsError is _UnassertedInteractionsError


def test_unused_mocks_error_importable() -> None:
    """UnusedMocksError must be importable from the top-level package."""
    from bigfoot import UnusedMocksError
    from bigfoot._errors import UnusedMocksError as _UnusedMocksError

    assert UnusedMocksError is _UnusedMocksError


def test_verification_error_importable() -> None:
    """VerificationError must be importable from the top-level package."""
    from bigfoot import VerificationError
    from bigfoot._errors import VerificationError as _VerificationError

    assert VerificationError is _VerificationError


def test_interaction_mismatch_error_importable() -> None:
    """InteractionMismatchError must be importable from the top-level package."""
    from bigfoot import InteractionMismatchError
    from bigfoot._errors import InteractionMismatchError as _InteractionMismatchError

    assert InteractionMismatchError is _InteractionMismatchError


def test_sandbox_not_active_error_importable() -> None:
    """SandboxNotActiveError must be importable from the top-level package."""
    from bigfoot import SandboxNotActiveError
    from bigfoot._errors import SandboxNotActiveError as _SandboxNotActiveError

    assert SandboxNotActiveError is _SandboxNotActiveError


def test_conflict_error_importable() -> None:
    """ConflictError must be importable from the top-level package."""
    from bigfoot import ConflictError
    from bigfoot._errors import ConflictError as _ConflictError

    assert ConflictError is _ConflictError


def test_missing_assertion_fields_error_importable() -> None:
    """MissingAssertionFieldsError must be importable from the top-level package."""
    from bigfoot import MissingAssertionFieldsError
    from bigfoot._errors import MissingAssertionFieldsError as _MissingAssertionFieldsError

    assert MissingAssertionFieldsError is _MissingAssertionFieldsError


def test_http_plugin_importable_if_http_extra_installed() -> None:
    """HttpPlugin must be importable from bigfoot if [http] extra is installed."""
    # ESCAPE: if HttpPlugin import was missing from __init__ when http extra is
    # installed, users would have to import from bigfoot.plugins.http directly
    try:
        import httpx  # noqa: F401
        import requests  # noqa: F401

        http_available = True
    except ImportError:
        http_available = False

    if not http_available:
        pytest.skip("http extra not installed")

    import bigfoot

    assert hasattr(bigfoot, "HttpPlugin")

    from bigfoot import HttpPlugin
    from bigfoot.plugins.http import HttpPlugin as _HttpPlugin

    assert HttpPlugin is _HttpPlugin


def test_no_active_verifier_error_importable() -> None:
    """NoActiveVerifierError must be importable from the top-level package."""
    from bigfoot import NoActiveVerifierError
    from bigfoot._errors import NoActiveVerifierError as _NoActiveVerifierError

    assert NoActiveVerifierError is _NoActiveVerifierError


def test_module_level_mock_importable() -> None:
    """bigfoot.mock must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.mock)


def test_module_level_sandbox_importable() -> None:
    """bigfoot.sandbox must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.sandbox)


def test_module_level_assert_interaction_importable() -> None:
    """bigfoot.assert_interaction must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.assert_interaction)


def test_module_level_in_any_order_importable() -> None:
    """bigfoot.in_any_order must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.in_any_order)


def test_module_level_verify_all_importable() -> None:
    """bigfoot.verify_all must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.verify_all)


def test_module_level_current_verifier_importable() -> None:
    """bigfoot.current_verifier must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.current_verifier)


def test_module_level_spy_importable() -> None:
    """bigfoot.spy must be importable as a callable."""
    import bigfoot

    assert callable(bigfoot.spy)


def test_module_level_http_importable() -> None:
    """bigfoot.http must be importable as an object."""
    import bigfoot

    assert bigfoot.http is not None


def test_module_level_mock_raises_no_active_verifier_error_outside_test() -> None:
    """bigfoot.mock() raises NoActiveVerifierError when called outside a test context."""
    import bigfoot
    from bigfoot._context import _current_test_verifier
    from bigfoot._errors import NoActiveVerifierError

    # Temporarily clear the test verifier to simulate being outside a test
    token = _current_test_verifier.set(None)
    try:
        with pytest.raises(NoActiveVerifierError):
            bigfoot.mock("os.path:sep")
    finally:
        _current_test_verifier.reset(token)


def test_spy_importable_from_bigfoot() -> None:
    """bigfoot.spy is importable and is callable."""
    import bigfoot

    assert callable(bigfoot.spy)


def test_missing_assertion_fields_error_importable_from_bigfoot() -> None:
    """MissingAssertionFieldsError is importable from the bigfoot namespace."""
    import bigfoot
    from bigfoot import MissingAssertionFieldsError

    assert issubclass(MissingAssertionFieldsError, bigfoot.BigfootError)


def test_spy_in_all() -> None:
    """'spy' is listed in bigfoot.__all__."""
    import bigfoot

    assert "spy" in bigfoot.__all__


def test_missing_assertion_fields_error_in_all() -> None:
    """'MissingAssertionFieldsError' is listed in bigfoot.__all__."""
    import bigfoot

    assert "MissingAssertionFieldsError" in bigfoot.__all__


def test_mock_accepts_path_parameter() -> None:
    """bigfoot.mock() accepts a path positional argument (new import-site API)."""
    import inspect

    import bigfoot

    sig = inspect.signature(bigfoot.mock)
    assert "path" in sig.parameters


def test_async_websocket_raises_import_error_when_websockets_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """async_websocket.__getattr__ raises ImportError with install instructions when websockets is not installed.

    ESCAPE: async_websocket
      CLAIM: Accessing any attribute on async_websocket raises ImportError with
             instructions when bigfoot.plugins.websocket_plugin._WEBSOCKETS_AVAILABLE is False.
      PATH:  _AsyncWebSocketProxy.__getattr__ -> checks _WEBSOCKETS_AVAILABLE -> raises ImportError.
      CHECK: Raises ImportError with message containing "bigfoot[websockets]" and "pip install".
      MUTATION: If __getattr__ does not check _WEBSOCKETS_AVAILABLE, the error is deferred to
                activate() time (inside a test context), and the message will be different or absent.
      ESCAPE: A proxy that checks availability but emits a wrong message would still pass the
              attribute access but fail only the message assertion -- caught by exact string check.
    """
    import bigfoot
    import bigfoot.plugins.websocket_plugin as ws_mod

    monkeypatch.setattr(ws_mod, "_WEBSOCKETS_AVAILABLE", False)

    with pytest.raises(ImportError) as exc_info:
        _ = bigfoot.async_websocket.new_session  # noqa: B018

    assert "bigfoot[websockets]" in str(exc_info.value)
    assert "pip install" in str(exc_info.value)


def test_bigfoot_module_is_context_manager(bigfoot_verifier: object) -> None:
    """``with bigfoot:`` activates a sandbox and returns the active StrictVerifier.

    ESCAPE: module context manager
      CLAIM: Entering ``with bigfoot:`` calls sandbox().__enter__() on the current
             verifier and returns the StrictVerifier instance.
      PATH:  _BigfootModule.__enter__ -> sandbox() -> SandboxContext.__enter__ -> returns verifier.
      CHECK: The ``as`` target is the StrictVerifier; calling mock/assert inside works normally.
      MUTATION: If __class__ swap is missing, ``with bigfoot:`` raises AttributeError.
      ESCAPE: A stub that returns *something* but not the verifier would fail the isinstance check.
    """
    import sys
    import types

    import bigfoot
    from bigfoot import StrictVerifier

    mod = types.ModuleType("_test_init_cm")
    mod.do = lambda: "real"  # type: ignore[attr-defined]
    sys.modules["_test_init_cm"] = mod
    try:
        mock = bigfoot.mock("_test_init_cm:do")
        mock.returns(42)

        with bigfoot as v:
            assert isinstance(v, StrictVerifier)
            result = mod.do()
            assert result == 42

        mock.assert_call(args=(), kwargs={})
    finally:
        del sys.modules["_test_init_cm"]


async def test_bigfoot_module_is_async_context_manager(bigfoot_verifier: object) -> None:
    """``async with bigfoot:`` activates a sandbox and returns the StrictVerifier.

    ESCAPE: async module context manager
      CLAIM: Entering ``async with bigfoot:`` delegates to sandbox().__aenter__() and
             returns the StrictVerifier.
      PATH:  _BigfootModule.__aenter__ -> sandbox() -> SandboxContext.__aenter__ -> returns verifier.
      CHECK: The ``as`` target is the StrictVerifier; async code inside the block is intercepted.
      MUTATION: Missing __aenter__ raises AttributeError; wrong return raises AssertionError.
    """
    import sys
    import types

    import bigfoot
    from bigfoot import StrictVerifier

    mod = types.ModuleType("_test_init_async_cm")
    mod.fetch = lambda: "real"  # type: ignore[attr-defined]
    sys.modules["_test_init_async_cm"] = mod
    try:
        mock = bigfoot.mock("_test_init_async_cm:fetch")
        mock.returns({"ok": True})

        async with bigfoot as v:
            assert isinstance(v, StrictVerifier)
            result = mod.fetch()
            assert result == {"ok": True}

        mock.assert_call(args=(), kwargs={})
    finally:
        del sys.modules["_test_init_async_cm"]


def test_bigfoot_nested_sandboxes_via_with_bigfoot(bigfoot_verifier: object) -> None:
    """Nested ``with bigfoot:`` blocks use reference counting and do not conflict.

    ESCAPE: nested sandboxes
      CLAIM: Entering ``with bigfoot:`` twice nests correctly; the inner exit does not
             deactivate plugins prematurely.
      PATH:  _BigfootModule.__enter__ pushes to stack twice; __exit__ pops in LIFO order.
      CHECK: Both ``as`` values are the same StrictVerifier; no errors on exit.
      MUTATION: A non-stacking implementation would push the same cm twice and break LIFO order.
    """
    import bigfoot
    from bigfoot import StrictVerifier

    with bigfoot as v1:
        with bigfoot as v2:
            assert isinstance(v1, StrictVerifier)
            assert isinstance(v2, StrictVerifier)
            assert v1 is v2


def test_sync_websocket_raises_import_error_when_websocket_client_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """sync_websocket.__getattr__ raises ImportError with install instructions when websocket-client is not installed.

    ESCAPE: sync_websocket
      CLAIM: Accessing any attribute on sync_websocket raises ImportError with
             instructions when bigfoot.plugins.websocket_plugin._WEBSOCKET_CLIENT_AVAILABLE is False.
      PATH:  _SyncWebSocketProxy.__getattr__ -> checks _WEBSOCKET_CLIENT_AVAILABLE -> raises ImportError.
      CHECK: Raises ImportError with message containing "bigfoot[websocket-client]" and "pip install".
      MUTATION: If __getattr__ does not check _WEBSOCKET_CLIENT_AVAILABLE, the error is deferred
                to activate() time (inside a test context), and the message will be different or absent.
      ESCAPE: A proxy that checks availability but emits a wrong message would still pass the
              attribute access but fail only the message assertion -- caught by exact string check.
    """
    import bigfoot
    import bigfoot.plugins.websocket_plugin as ws_mod

    monkeypatch.setattr(ws_mod, "_WEBSOCKET_CLIENT_AVAILABLE", False)

    with pytest.raises(ImportError) as exc_info:
        _ = bigfoot.sync_websocket.new_session  # noqa: B018

    assert "bigfoot[websocket-client]" in str(exc_info.value)
    assert "pip install" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Deprecated ``_mock`` aliases
# ---------------------------------------------------------------------------
#
# The 26 ``bigfoot.X_mock`` names are retained as deprecated aliases for the
# canonical un-suffixed proxy singletons (e.g. ``bigfoot.subprocess``).
# Accessing an alias must:
#   1. return the SAME object as the canonical proxy (identity, not equality);
#   2. emit a DeprecationWarning with a specific message on FIRST access only;
#   3. NOT emit a second warning on subsequent access of the same alias.
# Unknown attributes must still raise AttributeError with the standard message.
#
# We cover three representative aliases: ``subprocess_mock`` (always-available
# core), ``redis_mock`` (optional extra), and ``async_websocket_mock``
# (compound name). Exhaustive coverage of all 26 is unnecessary -- the
# behavior is driven by the same ``__getattr__`` hook.


@pytest.fixture
def _clear_warned_aliases():  # type: ignore[no-untyped-def]
    """Reset bigfoot's per-process ``_warned_aliases`` set so each test starts fresh.

    ``__getattr__`` only emits a DeprecationWarning the first time a given alias
    is accessed in a process. Other tests (or pytest collection itself) may have
    already triggered the warning, so we clear the set before the test runs and
    restore it afterwards.
    """
    import bigfoot

    snapshot = set(bigfoot._warned_aliases)
    bigfoot._warned_aliases.clear()
    yield
    bigfoot._warned_aliases.clear()
    bigfoot._warned_aliases.update(snapshot)


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("subprocess_mock", "subprocess"),
        ("redis_mock", "redis"),
        ("async_websocket_mock", "async_websocket"),
    ],
)
def test_deprecated_alias_returns_canonical_object(
    alias: str, canonical: str, _clear_warned_aliases: object
) -> None:
    """``bigfoot.<alias>`` returns the SAME object as ``bigfoot.<canonical>``.

    ESCAPE: deprecated alias identity
      CLAIM: Accessing the deprecated alias returns the identical proxy singleton
             that the canonical name returns -- not a copy, not a wrapper.
      PATH:  __getattr__ -> _DEPRECATED_PROXY_ALIASES.get(name) -> globals()[target].
      CHECK: ``alias_obj is canonical_obj`` (identity).
      MUTATION: A wrapper that delegates would pass equality but fail identity.
      ESCAPE: Returning a freshly constructed proxy each call would also fail identity.
    """
    import bigfoot

    canonical_obj = getattr(bigfoot, canonical)
    with pytest.warns(DeprecationWarning):
        alias_obj = getattr(bigfoot, alias)

    assert alias_obj is canonical_obj


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("subprocess_mock", "subprocess"),
        ("redis_mock", "redis"),
        ("async_websocket_mock", "async_websocket"),
    ],
)
def test_deprecated_alias_emits_deprecation_warning_on_first_access(
    alias: str, canonical: str, _clear_warned_aliases: object
) -> None:
    """First access of a deprecated alias emits a DeprecationWarning with exact text.

    ESCAPE: deprecated alias warning message
      CLAIM: First access emits a single DeprecationWarning whose message is
             exactly ``"bigfoot.<alias> is deprecated; use bigfoot.<canonical> instead."``.
      PATH:  __getattr__ -> warnings.warn(..., DeprecationWarning, stacklevel=2).
      CHECK: Exactly one warning recorded; category is DeprecationWarning;
             str(message) matches the exact expected text.
      MUTATION: Wrong category (e.g., FutureWarning) fails the category check.
                Wrong wording fails the exact string check.
      ESCAPE: Issuing two warnings on first access would fail the count check.
    """
    import bigfoot

    expected_message = f"bigfoot.{alias} is deprecated; use bigfoot.{canonical} instead."

    with pytest.warns(DeprecationWarning) as record:
        getattr(bigfoot, alias)

    matching = [w for w in record if str(w.message) == expected_message]
    assert len(matching) == 1, (
        f"expected exactly one DeprecationWarning with message "
        f"{expected_message!r}, got: {[str(w.message) for w in record]}"
    )
    assert matching[0].category is DeprecationWarning
    assert matching[0].filename.endswith("test_init.py"), (
        f"stacklevel should point to caller; got filename={matching[0].filename!r}"
    )


@pytest.mark.parametrize(
    ("alias", "canonical"),
    [
        ("subprocess_mock", "subprocess"),
        ("redis_mock", "redis"),
        ("async_websocket_mock", "async_websocket"),
    ],
)
def test_deprecated_alias_does_not_warn_on_second_access(
    alias: str, canonical: str, _clear_warned_aliases: object
) -> None:
    """Second access of the SAME alias in the same process emits no further warning.

    ESCAPE: alias warning is once-per-process
      CLAIM: __getattr__ tracks already-warned aliases via ``_warned_aliases`` and
             skips the ``warnings.warn`` call on subsequent access.
      PATH:  __getattr__ -> if name in _warned_aliases: skip warn -> return target.
      CHECK: After a first access (which emits the warning), a second access
             produces zero matching DeprecationWarnings.
      MUTATION: Removing the membership guard would emit the warning every access.
      ESCAPE: Tracking the canonical name instead of the alias would let two
              different aliases for the same target collide -- not what we test
              here, but the matching message check still catches that mistake.
    """
    import warnings as _warnings

    import bigfoot

    expected_message = f"bigfoot.{alias} is deprecated; use bigfoot.{canonical} instead."

    # Prime: trigger the first-access warning so the alias is registered in
    # _warned_aliases. We don't assert on this warning here -- a separate test
    # covers first-access semantics.
    with _warnings.catch_warnings():
        _warnings.simplefilter("ignore")
        getattr(bigfoot, alias)

    # Second access: must NOT emit any DeprecationWarning matching this alias.
    with _warnings.catch_warnings(record=True) as record:
        _warnings.simplefilter("always")
        getattr(bigfoot, alias)

    matching = [
        w for w in record
        if w.category is DeprecationWarning and str(w.message) == expected_message
    ]
    assert matching == [], (
        f"second access of bigfoot.{alias} unexpectedly emitted DeprecationWarning(s): "
        f"{[str(w.message) for w in matching]}"
    )


def test_unknown_attribute_raises_attribute_error(_clear_warned_aliases: object) -> None:
    """Accessing an unknown attribute on bigfoot raises AttributeError.

    ESCAPE: unknown attribute fallback
      CLAIM: Names not in ``_DEPRECATED_PROXY_ALIASES`` and not defined as real
             module globals raise AttributeError with the standard ``module
             'bigfoot' has no attribute 'X'`` message.
      PATH:  __getattr__ -> alias miss -> raise AttributeError(...).
      CHECK: AttributeError raised; message exactly matches the standard form.
      MUTATION: Returning ``None`` instead would fail the raises check.
                Wrong message text would fail the equality check.
      ESCAPE: Using ``hasattr`` instead of attribute access would swallow the error,
              so we test attribute access directly.
    """
    import bigfoot

    with pytest.raises(AttributeError) as exc_info:
        _ = bigfoot.not_a_thing  # type: ignore[attr-defined] # noqa: B018

    assert str(exc_info.value) == "module 'bigfoot' has no attribute 'not_a_thing'"
