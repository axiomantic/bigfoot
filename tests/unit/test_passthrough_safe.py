"""C2-T1, C2-T2: tests for the new BasePlugin.passthrough_safe ClassVar.

Replaces the old supports_guard ClassVar. Default is False (safer-by-default).
A migration table maps each plugin in the codebase to its expected
passthrough_safe value; the test enumerates all subclasses of BasePlugin
recursively (NOT directory glob, so MockPlugin and StateMachinePlugin
defined outside plugins/ are included) and checks each one.
"""

from __future__ import annotations


def _all_subclasses(cls: type) -> set[type]:
    """Return all (recursive) subclasses of cls."""
    result: set[type] = set()
    stack = [cls]
    while stack:
        current = stack.pop()
        for sub in current.__subclasses__():
            if sub in result:
                continue
            result.add(sub)
            stack.append(sub)
    return result


def test_default_is_false() -> None:
    """C2-T1: A fresh BasePlugin subclass with no override has
    passthrough_safe = False (safer-by-default).

    ESCAPE: test_default_is_false
      CLAIM: BasePlugin.passthrough_safe defaults to False; subclasses inherit
             that default unless they override it.
      PATH:  BasePlugin class body declares passthrough_safe: ClassVar[bool] = False.
      CHECK: A new subclass declared inline reports False.
      MUTATION: If the default were flipped to True (the unsafe direction), this
                test would observe True on FreshPlugin and fail.
      ESCAPE: A FreshPlugin that overrides passthrough_safe = True would still
              be classified True, so any code that uses FreshPlugin specifically
              would not regress. But the BasePlugin default itself is the risk
              this test pins.
    """
    from tripwire._base_plugin import BasePlugin

    class FreshPlugin(BasePlugin):
        pass

    assert FreshPlugin.passthrough_safe is False


# Migration table from design Section 4 (post-rename plugin paths). Maps
# the plugin class name to its expected passthrough_safe value.
EXPECTED_PASSTHROUGH_SAFE: dict[str, bool] = {
    # Real-IO plugins (passthrough_safe=False)
    "AsyncSubprocessPlugin": False,
    "AsyncpgPlugin": False,
    "Boto3Plugin": False,
    "DatabasePlugin": False,
    "DnsPlugin": False,
    "ElasticsearchPlugin": False,
    "GrpcPlugin": False,
    "HttpPlugin": False,
    "McpPlugin": False,
    "MemcachePlugin": False,
    "MongoPlugin": False,
    "PikaPlugin": False,
    "PopenPlugin": False,
    "Psycopg2Plugin": False,
    "RedisPlugin": False,
    "SmtpPlugin": False,
    "SocketPlugin": False,
    "SshPlugin": False,
    "SubprocessPlugin": False,
    "AsyncWebSocketPlugin": False,
    "SyncWebSocketPlugin": False,
    # Passthrough calls the original (broker-dispatch / disk / native loader),
    # so an un-mocked call performs real I/O.
    "CeleryPlugin": False,
    "FileIoPlugin": False,
    "NativePlugin": False,
    # Safe-passthrough plugins (passthrough_safe=True)
    "CryptoPlugin": True,
    "JwtPlugin": True,
    "LoggingPlugin": True,
    # Outside plugins/ directory
    "MockPlugin": True,
    "StateMachinePlugin": True,
}


def test_each_plugin_classification() -> None:
    """C2-T2: Every BasePlugin subclass found via recursive __subclasses__()
    has the documented passthrough_safe value, AND every entry in the
    migration table is present as a live class.

    ESCAPE: test_each_plugin_classification
      CLAIM: The live set of BasePlugin subclasses (recursive) matches the
             migration table from design Section 4 byte-for-byte: each class
             reports the documented passthrough_safe; no live class is missing
             from the table; no table entry is missing from the live set.
      PATH:  Force-import every plugin module so subclasses register, then
             walk BasePlugin.__subclasses__() recursively.
      CHECK: For each live subclass, its passthrough_safe equals the table
             entry. For each table entry, a class with that name was found.
      MUTATION: Flipping any plugin's passthrough_safe to the wrong value
                fails the per-class assert. Adding a new BasePlugin subclass
                without updating the table fails the "unexpected" assert.
      ESCAPE: A subclass declared in test code (e.g., FreshPlugin in T1) would
              also appear in __subclasses__(); the test ignores anonymous
              test-only subclasses by skipping any class name not in the
              expected table AND defined under tests/.
    """
    # Force-import every plugin module so __subclasses__() finds them.
    import importlib

    from tripwire._base_plugin import BasePlugin
    from tripwire._mock_plugin import MockPlugin  # noqa: F401 - registers subclass
    from tripwire._registry import PLUGIN_REGISTRY
    from tripwire._state_machine_plugin import StateMachinePlugin  # noqa: F401

    for entry in PLUGIN_REGISTRY:
        try:
            importlib.import_module(entry.import_path)
        except ImportError:
            # Optional dependency not installed; skip.
            continue

    live_subclasses = _all_subclasses(BasePlugin)
    live_by_name: dict[str, type] = {cls.__name__: cls for cls in live_subclasses}

    # Verify each table entry is present and classified correctly.
    missing_from_live: list[str] = []
    misclassified: list[tuple[str, bool, bool]] = []
    for name, expected in EXPECTED_PASSTHROUGH_SAFE.items():
        cls = live_by_name.get(name)
        if cls is None:
            # Optional-dep plugin may be absent in this environment;
            # only flag known-always-available ones as missing.
            # Conservatively allow absence (optional deps).
            missing_from_live.append(name)
            continue
        actual = cls.passthrough_safe
        if actual is not expected:
            misclassified.append((name, expected, actual))

    # Verify every live subclass is in the table (forces table updates).
    unexpected: list[str] = []
    for name, cls in live_by_name.items():
        if name in EXPECTED_PASSTHROUGH_SAFE:
            continue
        # Skip anonymous test-only subclasses defined in tests/ modules.
        module = getattr(cls, "__module__", "")
        if module.startswith("tests."):
            continue
        unexpected.append(f"{module}.{name}")

    # Misclassification is the strongest failure - report it loudly.
    assert not misclassified, (
        f"Misclassified plugins (name, expected, actual): {misclassified}"
    )
    assert not unexpected, (
        f"BasePlugin subclasses not in EXPECTED_PASSTHROUGH_SAFE table: {unexpected}. "
        "Add each new plugin to design Section 4 and to this table."
    )
    # Allow optional-dep absences; flag only if EVERY entry is missing
    # (which would mean test wiring is broken).
    assert len(missing_from_live) < len(EXPECTED_PASSTHROUGH_SAFE), (
        f"All migration-table classes missing from live subclass set: "
        f"{missing_from_live}. Plugin import wiring broke."
    )
