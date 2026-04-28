"""Plugin registry for always-on auto-activation."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final

if TYPE_CHECKING:
    from tripwire._base_plugin import BasePlugin


@dataclass(frozen=True)
class PluginEntry:
    """Registry entry for a single plugin."""

    name: str  # canonical registry name (e.g., "http")
    import_path: str  # e.g., "tripwire.plugins.http"
    class_name: str  # e.g., "HttpPlugin"
    availability_check: str  # module path or flag path to check availability
    default_enabled: bool = True  # False for opt-in plugins (e.g., file I/O, ctypes/cffi)


def _check_dep_available(module_name: str) -> bool:
    """Return True if a third-party dependency module is importable."""
    try:
        __import__(module_name)
        return True
    except ImportError:
        return False


def _check_plugin_flag(import_path: str, flag_name: str) -> bool:
    """Import a plugin module and read its availability flag."""
    import importlib

    module = importlib.import_module(import_path)
    return getattr(module, flag_name, False)


def _is_available(entry: PluginEntry) -> bool:
    """Determine if a plugin's optional dependencies are satisfied.

    Convention-based availability check using the availability_check field:
    - "always": No optional deps; always available
    - "<module_name>": Single module; try to import it
    - "<mod1>+<mod2>": Multiple modules; all must be importable
    - "flag:<import_path>:<flag_name>": Read a boolean flag from a plugin module
    """
    check = entry.availability_check

    if check == "always":
        return True

    if check.startswith("flag:"):
        _, import_path, flag_name = check.split(":", 2)
        return _check_plugin_flag(import_path, flag_name)

    if "+" in check:
        return all(_check_dep_available(m) for m in check.split("+"))

    # Default: single module check
    return _check_dep_available(check)


# Registry of all interceptor plugins (excludes MockPlugin).
PLUGIN_REGISTRY: tuple[PluginEntry, ...] = (
    PluginEntry("http", "tripwire.plugins.http", "HttpPlugin", "httpx+requests"),
    PluginEntry("subprocess", "tripwire.plugins.subprocess", "SubprocessPlugin", "always"),
    PluginEntry("popen", "tripwire.plugins.popen_plugin", "PopenPlugin", "always"),
    PluginEntry("smtp", "tripwire.plugins.smtp_plugin", "SmtpPlugin", "always"),
    PluginEntry("socket", "tripwire.plugins.socket_plugin", "SocketPlugin", "always"),
    PluginEntry("database", "tripwire.plugins.database_plugin", "DatabasePlugin", "always"),
    PluginEntry(
        "async_websocket",
        "tripwire.plugins.websocket_plugin",
        "AsyncWebSocketPlugin",
        "websockets",
    ),
    PluginEntry(
        "sync_websocket",
        "tripwire.plugins.websocket_plugin",
        "SyncWebSocketPlugin",
        "flag:tripwire.plugins.websocket_plugin:_WEBSOCKET_CLIENT_AVAILABLE",
    ),
    PluginEntry("redis", "tripwire.plugins.redis_plugin", "RedisPlugin", "redis"),
    PluginEntry("psycopg2", "tripwire.plugins.psycopg2_plugin", "Psycopg2Plugin", "psycopg2"),
    PluginEntry("asyncpg", "tripwire.plugins.asyncpg_plugin", "AsyncpgPlugin", "asyncpg"),
    PluginEntry("logging", "tripwire.plugins.logging_plugin", "LoggingPlugin", "always"),
    PluginEntry(
        "async_subprocess",
        "tripwire.plugins.async_subprocess_plugin",
        "AsyncSubprocessPlugin",
        "always",
    ),
    PluginEntry("dns", "tripwire.plugins.dns_plugin", "DnsPlugin", "always"),
    PluginEntry("memcache", "tripwire.plugins.memcache_plugin", "MemcachePlugin", "pymemcache"),
    PluginEntry("celery", "tripwire.plugins.celery_plugin", "CeleryPlugin", "celery"),
    PluginEntry("boto3", "tripwire.plugins.boto3_plugin", "Boto3Plugin", "boto3"),
    PluginEntry(
        "elasticsearch",
        "tripwire.plugins.elasticsearch_plugin",
        "ElasticsearchPlugin",
        "elasticsearch",
    ),
    PluginEntry("jwt", "tripwire.plugins.jwt_plugin", "JwtPlugin", "jwt"),
    PluginEntry("crypto", "tripwire.plugins.crypto_plugin", "CryptoPlugin", "cryptography"),
    PluginEntry("mongo", "tripwire.plugins.mongo_plugin", "MongoPlugin", "pymongo"),
    PluginEntry(
        "file_io", "tripwire.plugins.file_io_plugin", "FileIoPlugin",
        "always", default_enabled=False,
    ),
    PluginEntry("pika", "tripwire.plugins.pika_plugin", "PikaPlugin", "pika"),
    PluginEntry("ssh", "tripwire.plugins.ssh_plugin", "SshPlugin", "paramiko"),
    PluginEntry("grpc", "tripwire.plugins.grpc_plugin", "GrpcPlugin", "grpc"),
    PluginEntry("mcp", "tripwire.plugins.mcp_plugin", "McpPlugin", "mcp"),
    PluginEntry(
        "native", "tripwire.plugins.native_plugin", "NativePlugin",
        "always", default_enabled=False,
    ),
)

VALID_PLUGIN_NAMES: frozenset[str] = frozenset(e.name for e in PLUGIN_REGISTRY)

def get_plugin_class(entry: PluginEntry) -> type[BasePlugin]:
    """Import and return the plugin class for a registry entry."""
    import importlib

    module = importlib.import_module(entry.import_path)
    cls: type[BasePlugin] = getattr(module, entry.class_name)
    return cls


# ---------------------------------------------------------------------------
# Hot-path lookup cache
#
# ``lookup_plugin_class_by_name`` runs on EVERY intercepted call from a
# sandbox (every subprocess.run, socket.send, logging.debug, etc.) via
# ``get_verifier_or_raise``. The uncached implementation iterates the
# registry, runs availability checks (which import modules), and imports
# the plugin class on every call: O(N) work over ~27 plugins per dispatch.
#
# The registry is effectively immutable for the life of the process
# (entries are added at module import; availability can flip only by
# installing a new package, which requires a process restart). We
# therefore eagerly populate the cache exactly once at module import time
# (see ``_populate_lookup_cache()`` below), seeding both canonical names
# and every declared ``guard_prefix``.
#
# Thread-safety contract: after import-time population, the read path is
# LOCK-FREE. Only the never-before-seen-name slow path takes
# ``_lookup_cache_lock`` to memoize a None result. Hot-path callers
# (canonical names + registered guard_prefixes) hit a plain
# ``dict.get`` and return immediately. Stock CPython's GIL serializes
# dict reads; the free-threaded build (PEP 703) makes ``dict.get`` of a
# stable key atomic, and the cache is effectively immutable for known
# names after import.
#
# Tests that monkeypatch ``PLUGIN_REGISTRY`` MUST clear the cache via
# ``_clear_lookup_cache()`` for their patch to take effect.
# ---------------------------------------------------------------------------

_UNSET: Final[object] = object()
_lookup_cache: dict[str, tuple[type[BasePlugin], str] | None] = {}
_lookup_cache_lock: Final[threading.Lock] = threading.Lock()


def _populate_lookup_cache() -> None:
    """Eagerly seed ``_lookup_cache`` from ``PLUGIN_REGISTRY``.

    For every available entry, this imports the plugin class and inserts
    cache entries keyed by both the canonical registry name and every
    declared ``guard_prefixes`` value. After this runs, all known plugin
    names and prefixes resolve via a lock-free ``dict.get`` on the read
    path. Unknown names still fall through to the locked negative-cache
    slow path in ``lookup_plugin_class_by_name``.

    Called exactly once at module import time. Also called by
    ``_clear_lookup_cache`` to restore the eager state after a test
    invalidates the cache.

    Failures to import a single plugin class are swallowed: the entry is
    simply not seeded, and a subsequent lookup will go through the slow
    path (and likely return None for that name). This preserves the
    original lazy behavior for broken/partially-installed plugins.
    """
    for entry in PLUGIN_REGISTRY:
        if not _is_available(entry):
            continue
        try:
            cls = get_plugin_class(entry)
        except Exception:
            continue
        payload: tuple[type[BasePlugin], str] = (cls, entry.name)
        _lookup_cache[entry.name] = payload
        for prefix in getattr(cls, "guard_prefixes", ()):
            # Canonical name takes precedence if a prefix collides with
            # another plugin's canonical name; do not overwrite.
            _lookup_cache.setdefault(prefix, payload)


def _clear_lookup_cache() -> None:
    """Drop all cached ``lookup_plugin_class_by_name`` results, then
    re-seed the eager entries.

    Call this from tests that monkeypatch ``PLUGIN_REGISTRY`` so their
    substitute registry is consulted instead of stale cache entries.
    The re-population step ensures that the lock-free read path remains
    valid for normal (unpatched) registry entries after the test
    teardown clears the cache. Tests that monkeypatch ``PLUGIN_REGISTRY``
    will pick up the patched registry on the next ``_populate_lookup_cache``
    invocation, since this function reads ``PLUGIN_REGISTRY`` at call
    time rather than at import time.
    """
    with _lookup_cache_lock:
        _lookup_cache.clear()
        _populate_lookup_cache()


def lookup_plugin_class_by_name(
    plugin_name: str,
) -> tuple[type[BasePlugin], str] | None:
    """Return ``(plugin_class, canonical_registry_name)`` registered under
    ``plugin_name``, or None.

    Looks up by canonical registry name first, then by any ``guard_prefixes``
    declared on a registered plugin class. Returns None when no plugin
    matches or when its optional dependency is missing. Callers use this
    from outside any active sandbox to ask "what plugin would receive a
    call from this source_id?".

    The canonical name is ``entry.name`` (the registry name, e.g.
    ``"database"``). It may differ from ``plugin_name`` when ``plugin_name``
    matches a ``guard_prefix`` instead (e.g., ``plugin_name="db"`` resolves
    to ``("DatabasePlugin", "database")``). Callers MUST use the canonical
    name when looking up per-protocol guard overrides and when populating
    ``plugin_name`` on errors so the user sees the registry name.

    Read path is lock-free: ``_lookup_cache`` is eagerly populated at
    module import time, so all known plugin names and guard prefixes
    resolve via a plain dict ``get``. Only never-before-seen names take
    ``_lookup_cache_lock`` to negatively cache the None result. Tests
    that mutate ``PLUGIN_REGISTRY`` must call ``_clear_lookup_cache()``
    for changes to be observed.
    """
    # Lock-free fast path. After import-time population, every known
    # canonical name and guard_prefix is a hit; only unseen names miss.
    cached = _lookup_cache.get(plugin_name, _UNSET)
    if cached is not _UNSET:
        # mypy cannot narrow through the sentinel object; we know the
        # cached value is the tuple-or-None payload, not the sentinel.
        return cached  # type: ignore[return-value]

    # Slow path: name not in cache. Take the lock for negative caching
    # so concurrent callers don't all repeat the (None) computation. The
    # eager populator already covered all canonical names and declared
    # prefixes, so reaching here for an available plugin is impossible
    # in practice; this branch exists to memoize unknown-name lookups.
    with _lookup_cache_lock:
        # Re-check: another thread may have raced us through the lock
        # and populated the entry already.
        cached = _lookup_cache.get(plugin_name, _UNSET)
        if cached is not _UNSET:
            return cached  # type: ignore[return-value]
        _lookup_cache[plugin_name] = None
        return None


def resolve_enabled_plugins(
    config: dict[str, object],
) -> list[PluginEntry]:
    """Determine which plugins to auto-instantiate based on config.

    Config keys (mutually exclusive):
    - enabled_plugins: list[str] - allowlist (only these)
    - disabled_plugins: list[str] - blocklist (all except these)
    - neither: all available plugins

    Raises TripwireConfigError for:
    - Both keys present
    - Unknown plugin names
    - Invalid types (not a list)
    """
    from tripwire._errors import TripwireConfigError

    enabled = config.get("enabled_plugins")
    disabled = config.get("disabled_plugins")

    if enabled is not None and disabled is not None:
        raise TripwireConfigError(
            "enabled_plugins and disabled_plugins are mutually exclusive. "
            "Use one or the other, not both."
        )

    # Type validation: must be lists if present
    if enabled is not None and not isinstance(enabled, list):
        raise TripwireConfigError(
            f"enabled_plugins must be a list of strings, got {type(enabled).__name__}"
        )
    if disabled is not None and not isinstance(disabled, list):
        raise TripwireConfigError(
            f"disabled_plugins must be a list of strings, got {type(disabled).__name__}"
        )

    if enabled is not None:
        unknown = set(enabled) - VALID_PLUGIN_NAMES
        if unknown:
            raise TripwireConfigError(
                f"Unknown plugin name(s) in enabled_plugins: {sorted(unknown)}. "
                f"Valid names: {sorted(VALID_PLUGIN_NAMES)}"
            )
        result = []
        for e in PLUGIN_REGISTRY:
            if e.name in enabled:
                if not _is_available(e):
                    raise TripwireConfigError(
                        f"Plugin '{e.name}' is in enabled_plugins but its "
                        f"dependency '{e.availability_check}' is not installed. "
                        f"Install with: pip install python-tripwire[{e.name}]"
                    )
                result.append(e)
        return result

    if disabled is not None:
        unknown = set(disabled) - VALID_PLUGIN_NAMES
        if unknown:
            raise TripwireConfigError(
                f"Unknown plugin name(s) in disabled_plugins: {sorted(unknown)}. "
                f"Valid names: {sorted(VALID_PLUGIN_NAMES)}"
            )
        return [
            e for e in PLUGIN_REGISTRY
            if e.name not in disabled and e.default_enabled and _is_available(e)
        ]

    # Default: all available plugins that are default-enabled
    return [e for e in PLUGIN_REGISTRY if e.default_enabled and _is_available(e)]


# Eagerly seed ``_lookup_cache`` exactly once at module import time. After
# this runs, every known canonical name and registered ``guard_prefix``
# is a lock-free dict hit on the hot path. See the module-level cache
# comment block above for the full thread-safety contract.
_populate_lookup_cache()
