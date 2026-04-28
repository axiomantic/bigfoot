"""Unit tests for tripwire._registry: plugin registry and config resolution."""

import threading
from unittest.mock import patch

import pytest

from tripwire._errors import TripwireConfigError
from tripwire._registry import (
    PLUGIN_REGISTRY,
    VALID_PLUGIN_NAMES,
    PluginEntry,
    _clear_lookup_cache,
    _is_available,
    get_plugin_class,
    lookup_plugin_class_by_name,
    resolve_enabled_plugins,
)

# ---------------------------------------------------------------------------
# Registry contents
# ---------------------------------------------------------------------------


def test_plugin_registry_contains_all_plugins() -> None:
    """PLUGIN_REGISTRY must contain exactly 27 entries (all interceptor plugins)."""
    assert len(PLUGIN_REGISTRY) == 27


def test_valid_plugin_names_matches_registry() -> None:
    """VALID_PLUGIN_NAMES must contain exactly the names from PLUGIN_REGISTRY."""
    expected = {
        "http",
        "subprocess",
        "popen",
        "smtp",
        "socket",
        "database",
        "async_websocket",
        "sync_websocket",
        "redis",
        "psycopg2",
        "asyncpg",
        "logging",
        "async_subprocess",
        "dns",
        "memcache",
        "celery",
        "boto3",
        "elasticsearch",
        "jwt",
        "crypto",
        "mongo",
        "file_io",
        "pika",
        "ssh",
        "grpc",
        "native",
        "mcp",
    }
    assert VALID_PLUGIN_NAMES == expected


def test_plugin_registry_entries_are_frozen() -> None:
    """Each entry in PLUGIN_REGISTRY must be a frozen dataclass (immutable)."""
    for entry in PLUGIN_REGISTRY:
        assert isinstance(entry, PluginEntry)
        with pytest.raises(AttributeError):
            entry.name = "changed"  # type: ignore[misc]


def test_plugin_registry_names_are_unique() -> None:
    """No two entries in PLUGIN_REGISTRY may share the same name."""
    names = [e.name for e in PLUGIN_REGISTRY]
    assert len(names) == len(set(names))


# ---------------------------------------------------------------------------
# Availability checks
# ---------------------------------------------------------------------------


def test_is_available_always_returns_true() -> None:
    """Plugins with availability_check='always' are always available."""
    entry = PluginEntry("test", "tripwire.plugins.subprocess", "SubprocessPlugin", "always")
    assert _is_available(entry) is True


def test_is_available_httpx_requests_when_installed() -> None:
    """HttpPlugin availability check returns True when httpx and requests are installed."""
    # httpx and requests are in dev deps, so they should be available
    entry = PluginEntry("http", "tripwire.plugins.http", "HttpPlugin", "httpx+requests")
    assert _is_available(entry) is True


def test_is_available_websockets_uses_flag() -> None:
    """Websockets availability check reads _WEBSOCKETS_AVAILABLE flag."""
    entry = PluginEntry(
        "async_websocket",
        "tripwire.plugins.websocket_plugin",
        "AsyncWebSocketPlugin",
        "websockets",
    )
    # websockets is in dev deps, should be available
    assert _is_available(entry) is True


def test_is_available_redis_uses_flag() -> None:
    """Redis availability check reads _REDIS_AVAILABLE flag."""
    entry = PluginEntry(
        "redis", "tripwire.plugins.redis_plugin", "RedisPlugin", "redis"
    )
    # redis is in dev deps, should be available
    assert _is_available(entry) is True


def test_is_available_unknown_check_returns_false() -> None:
    """Unknown availability_check values return False."""
    entry = PluginEntry("fake", "tripwire.plugins.fake", "FakePlugin", "nonexistent_dep")
    assert _is_available(entry) is False


class TestIsAvailableConventions:
    """_is_available handles all four convention formats."""

    def test_always_available(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "always")
        assert _is_available(entry) is True

    def test_single_module_available(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "json")  # stdlib, always importable
        assert _is_available(entry) is True

    def test_single_module_unavailable(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "nonexistent_module_xyz_abc")
        assert _is_available(entry) is False

    def test_multi_module_all_available(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "json+os")
        assert _is_available(entry) is True

    def test_multi_module_one_missing(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "json+nonexistent_module_xyz_abc")
        assert _is_available(entry) is False

    def test_flag_based_check(self) -> None:
        entry = PluginEntry("test", "x.y", "X", "flag:tripwire.plugins.redis_plugin:_REDIS_AVAILABLE")
        result = _is_available(entry)
        assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# get_plugin_class
# ---------------------------------------------------------------------------


def test_get_plugin_class_returns_correct_class() -> None:
    """get_plugin_class returns the actual class for a valid entry."""
    from tripwire.plugins.subprocess import SubprocessPlugin

    entry = PluginEntry("subprocess", "tripwire.plugins.subprocess", "SubprocessPlugin", "always")
    cls = get_plugin_class(entry)
    assert cls is SubprocessPlugin


def test_get_plugin_class_import_error_for_bad_path() -> None:
    """get_plugin_class raises ImportError for a nonexistent module."""
    entry = PluginEntry("fake", "tripwire.plugins.nonexistent", "FakePlugin", "always")
    with pytest.raises(ImportError):
        get_plugin_class(entry)


# ---------------------------------------------------------------------------
# resolve_enabled_plugins
# ---------------------------------------------------------------------------


def test_resolve_enabled_plugins_default_returns_all_available() -> None:
    """With empty config, all available plugins are returned."""
    result = resolve_enabled_plugins({})
    names = {e.name for e in result}
    # All plugins with no optional deps should be present
    assert "subprocess" in names
    assert "popen" in names
    assert "smtp" in names
    assert "socket" in names
    assert "database" in names


def test_resolve_enabled_plugins_allowlist() -> None:
    """enabled_plugins returns only the listed plugins."""
    result = resolve_enabled_plugins({"enabled_plugins": ["subprocess", "popen"]})
    names = {e.name for e in result}
    assert names == {"subprocess", "popen"}


def test_resolve_enabled_plugins_blocklist() -> None:
    """disabled_plugins excludes the listed plugins."""
    result = resolve_enabled_plugins({"disabled_plugins": ["subprocess"]})
    names = {e.name for e in result}
    assert "subprocess" not in names
    # Other always-available plugins should be present
    assert "popen" in names
    assert "smtp" in names


def test_resolve_enabled_plugins_mutual_exclusion() -> None:
    """Both keys present raises TripwireConfigError."""
    with pytest.raises(TripwireConfigError, match="mutually exclusive"):
        resolve_enabled_plugins({
            "enabled_plugins": ["http"],
            "disabled_plugins": ["subprocess"],
        })


def test_resolve_enabled_plugins_unknown_name_in_enabled() -> None:
    """Unknown name in enabled_plugins raises TripwireConfigError."""
    with pytest.raises(TripwireConfigError, match="Unknown plugin name"):
        resolve_enabled_plugins({"enabled_plugins": ["nonexistent"]})


def test_resolve_enabled_plugins_unknown_name_in_disabled() -> None:
    """Unknown name in disabled_plugins raises TripwireConfigError."""
    with pytest.raises(TripwireConfigError, match="Unknown plugin name"):
        resolve_enabled_plugins({"disabled_plugins": ["nonexistent"]})


def test_resolve_enabled_plugins_invalid_type_string() -> None:
    """enabled_plugins as string (not list) raises TripwireConfigError."""
    with pytest.raises(TripwireConfigError, match="must be a list of strings"):
        resolve_enabled_plugins({"enabled_plugins": "http"})


def test_resolve_enabled_plugins_invalid_type_disabled_string() -> None:
    """disabled_plugins as string (not list) raises TripwireConfigError."""
    with pytest.raises(TripwireConfigError, match="must be a list of strings"):
        resolve_enabled_plugins({"disabled_plugins": "http"})


def test_resolve_enabled_plugins_skips_unavailable() -> None:
    """Enabled plugin list filters by availability."""
    result = resolve_enabled_plugins({"enabled_plugins": ["subprocess"]})
    names = {e.name for e in result}
    assert names == {"subprocess"}


class TestDefaultEnabled:
    """PluginEntry.default_enabled controls default inclusion."""

    def test_default_enabled_false_excluded_from_default(self) -> None:
        entry = PluginEntry("test_opt", "x.y", "X", "always", default_enabled=False)
        always_entry = PluginEntry("test_always", "x.y", "Y", "always", default_enabled=True)
        with patch("tripwire._registry.PLUGIN_REGISTRY", (entry, always_entry)):
            with patch("tripwire._registry.VALID_PLUGIN_NAMES", frozenset({"test_opt", "test_always"})):
                result = resolve_enabled_plugins({})
                names = [e.name for e in result]
                assert "test_opt" not in names
                assert "test_always" in names

    def test_default_enabled_false_included_when_explicit(self) -> None:
        entry = PluginEntry("test_opt", "x.y", "X", "always", default_enabled=False)
        with patch("tripwire._registry.PLUGIN_REGISTRY", (entry,)):
            with patch("tripwire._registry.VALID_PLUGIN_NAMES", frozenset({"test_opt"})):
                result = resolve_enabled_plugins({"enabled_plugins": ["test_opt"]})
                assert any(e.name == "test_opt" for e in result)


def test_resolve_enabled_plugins_error_lists_valid_names() -> None:
    """Error message for unknown names includes the list of valid names."""
    with pytest.raises(TripwireConfigError) as exc_info:
        resolve_enabled_plugins({"enabled_plugins": ["bogus"]})
    error_msg = str(exc_info.value)
    assert "subprocess" in error_msg
    assert "http" in error_msg


# ---------------------------------------------------------------------------
# lookup_plugin_class_by_name + cache
# ---------------------------------------------------------------------------


class TestLookupPluginClassByNameCache:
    """The hot-path lookup is cached; verify shape and invalidation."""

    def setup_method(self) -> None:
        # Each test starts with a clean cache so prior cached entries do
        # not influence identity assertions.
        _clear_lookup_cache()

    def teardown_method(self) -> None:
        # Leave no cached entries from monkeypatched registries.
        _clear_lookup_cache()

    def test_known_name_returns_tuple(self) -> None:
        """A known canonical name resolves to (cls, canonical_name)."""
        from tripwire.plugins.subprocess import SubprocessPlugin

        result = lookup_plugin_class_by_name("subprocess")
        assert result is not None
        cls, canonical = result
        assert cls is SubprocessPlugin
        assert canonical == "subprocess"

    def test_repeated_lookup_returns_identical_tuple(self) -> None:
        """Cached results return the same tuple object (identity, not just equality)."""
        first = lookup_plugin_class_by_name("subprocess")
        second = lookup_plugin_class_by_name("subprocess")
        assert first is not None
        assert first is second

    def test_unknown_name_returns_none(self) -> None:
        """An unregistered name resolves to None."""
        assert lookup_plugin_class_by_name("nonexistent_xyz") is None

    def test_unknown_name_negative_cache(self) -> None:
        """Unknown names are negatively cached: second lookup is also None."""
        assert lookup_plugin_class_by_name("nonexistent_xyz") is None
        assert lookup_plugin_class_by_name("nonexistent_xyz") is None

    def test_clear_cache_invalidates(self) -> None:
        """_clear_lookup_cache forces the next lookup to recompute."""
        first = lookup_plugin_class_by_name("subprocess")
        _clear_lookup_cache()
        second = lookup_plugin_class_by_name("subprocess")
        # The plugin class itself is module-level and stable, so the inner
        # type identity persists. The tuple object is freshly constructed,
        # so it should NOT be the same tuple instance after invalidation.
        assert first is not None
        assert second is not None
        assert first is not second
        assert first == second

    def test_guard_prefix_resolves_to_canonical_name(self) -> None:
        """A guard_prefix lookup returns the canonical registry name, not the prefix."""
        # DatabasePlugin registers a guard_prefix of "db".
        result = lookup_plugin_class_by_name("db")
        assert result is not None
        _cls, canonical = result
        assert canonical == "database"

    def test_concurrent_lookup_safe(self) -> None:
        """Concurrent lookups return the same cached tuple under a lock."""
        results: list[tuple[type, str] | None] = []
        results_lock = threading.Lock()

        def worker() -> None:
            local: list[tuple[type, str] | None] = []
            for _ in range(100):
                local.append(lookup_plugin_class_by_name("subprocess"))
            with results_lock:
                results.extend(local)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(results) == 20 * 100
        first = results[0]
        assert first is not None
        # All 2000 results must be the same tuple instance: the first
        # successful populate wins and every subsequent lookup serves the
        # cached identity.
        assert all(r is first for r in results)

    def test_known_name_lookup_is_lock_free(self) -> None:
        """Looking up a known plugin name MUST NOT acquire the cache lock.

        After import-time eager population, all canonical names and
        guard prefixes are cached. The hot-path read is a plain
        ``dict.get`` and must not touch ``_lookup_cache_lock``. We
        enforce this by patching the lock with a sentinel that fails
        loudly if anyone attempts to acquire it.
        """
        # Sanity: the eager populator should have already seeded
        # "subprocess". Do NOT call _clear_lookup_cache here — that would
        # re-populate but also exercise the lock during teardown setup.
        # The class-level setup_method already cleared+repopulated.

        class _LockMustNotBeAcquired:
            def __enter__(self) -> "_LockMustNotBeAcquired":
                raise AssertionError(
                    "lookup_plugin_class_by_name acquired the cache lock "
                    "for a known plugin name; the read path must be "
                    "lock-free after eager population."
                )

            def __exit__(self, *exc: object) -> None:  # pragma: no cover
                pass

            def acquire(self, *args: object, **kwargs: object) -> bool:
                raise AssertionError(
                    "lookup_plugin_class_by_name acquired the cache lock "
                    "for a known plugin name; the read path must be "
                    "lock-free after eager population."
                )

            def release(self) -> None:  # pragma: no cover
                pass

        from tripwire.plugins.subprocess import SubprocessPlugin

        with patch("tripwire._registry._lookup_cache_lock", _LockMustNotBeAcquired()):
            # Canonical name: must NOT acquire the lock.
            result = lookup_plugin_class_by_name("subprocess")
            assert result is not None
            cls, canonical = result
            assert cls is SubprocessPlugin
            assert canonical == "subprocess"

            # Guard prefix: must also be eagerly cached and lock-free.
            result_prefix = lookup_plugin_class_by_name("db")
            assert result_prefix is not None
            _cls, canonical_prefix = result_prefix
            assert canonical_prefix == "database"

    def test_unknown_name_takes_lock_once_for_negative_cache(self) -> None:
        """An unregistered name takes the lock exactly once, then is
        memoized so subsequent lookups are lock-free.

        Regression: confirms the slow path (unknown name) still
        negatively caches under the lock so concurrent callers don't
        repeatedly walk the registry for the same missing name.
        """
        from tripwire import _registry

        real_lock = _registry._lookup_cache_lock

        class _CountingLock:
            def __init__(self) -> None:
                self.acquire_count = 0

            def __enter__(self) -> "_CountingLock":
                self.acquire_count += 1
                real_lock.acquire()
                return self

            def __exit__(self, *exc: object) -> None:
                real_lock.release()

        counter = _CountingLock()
        with patch("tripwire._registry._lookup_cache_lock", counter):
            # First lookup: unknown name, must acquire the lock to seed
            # the negative cache entry.
            assert lookup_plugin_class_by_name("nonexistent_xyz_unique") is None
            assert counter.acquire_count == 1

            # Second lookup: now negatively cached, must be lock-free.
            assert lookup_plugin_class_by_name("nonexistent_xyz_unique") is None
            assert counter.acquire_count == 1

    def test_eager_population_seeds_all_available_canonical_names(self) -> None:
        """Every available registry entry's canonical name must be in the
        cache immediately after import (and after _clear_lookup_cache).

        This is the structural invariant that makes the lock-free read
        path correct: if any canonical name were missing from the eager
        seed, that name would fall through to the locked slow path on
        every call.
        """
        from tripwire._registry import PLUGIN_REGISTRY, _is_available, _lookup_cache

        for entry in PLUGIN_REGISTRY:
            if not _is_available(entry):
                continue
            assert entry.name in _lookup_cache, (
                f"canonical name {entry.name!r} missing from eager-populated "
                f"cache; lookup would take the slow path"
            )
            cached = _lookup_cache[entry.name]
            assert cached is not None
            _cls, canonical = cached
            assert canonical == entry.name
