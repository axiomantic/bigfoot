"""Type stubs for bigfoot's dynamic module-level API.

Enables Pyright/mypy to resolve:
- ``with bigfoot:`` context manager protocol
- Module-level functions (current_verifier, sandbox, assert_interaction, etc.)
- Module-level factories (mock, spy)
- Plugin proxy attributes (http, subprocess, etc.)
- All error classes
"""

from __future__ import annotations

import types
from typing import Any

from bigfoot._base_plugin import BasePlugin as BasePlugin
from bigfoot._context import GuardPassThrough as GuardPassThrough
from bigfoot._context import get_verifier_or_raise as get_verifier_or_raise
from bigfoot._errors import AllWildcardAssertionError as AllWildcardAssertionError
from bigfoot._errors import AssertionInsideSandboxError as AssertionInsideSandboxError
from bigfoot._errors import AutoAssertError as AutoAssertError
from bigfoot._errors import BigfootConfigError as BigfootConfigError
from bigfoot._errors import BigfootError as BigfootError
from bigfoot._errors import ConflictError as ConflictError
from bigfoot._errors import GuardedCallError as GuardedCallError
from bigfoot._errors import GuardedCallWarning as GuardedCallWarning
from bigfoot._errors import InteractionMismatchError as InteractionMismatchError
from bigfoot._errors import InvalidStateError as InvalidStateError
from bigfoot._errors import MissingAssertionFieldsError as MissingAssertionFieldsError
from bigfoot._errors import NoActiveVerifierError as NoActiveVerifierError
from bigfoot._errors import SandboxNotActiveError as SandboxNotActiveError
from bigfoot._errors import UnassertedInteractionsError as UnassertedInteractionsError
from bigfoot._errors import UnmockedInteractionError as UnmockedInteractionError
from bigfoot._errors import UnusedMocksError as UnusedMocksError
from bigfoot._errors import VerificationError as VerificationError
from bigfoot._guard import allow as allow
from bigfoot._guard import deny as deny
from bigfoot._mock_plugin import ImportSiteMock, ObjectMock
from bigfoot._mock_plugin import MockPlugin as MockPlugin
from bigfoot._registry import PluginEntry as PluginEntry
from bigfoot._registry import is_guard_eligible as is_guard_eligible
from bigfoot._timeline import Interaction as Interaction
from bigfoot._timeline import Timeline as Timeline
from bigfoot._verifier import InAnyOrderContext as InAnyOrderContext
from bigfoot._verifier import SandboxContext as SandboxContext
from bigfoot._verifier import StrictVerifier as StrictVerifier
from bigfoot.plugins.async_subprocess_plugin import (
    AsyncSubprocessPlugin as AsyncSubprocessPlugin,
)
from bigfoot.plugins.database_plugin import DatabasePlugin as DatabasePlugin
from bigfoot.plugins.dns_plugin import DnsPlugin as DnsPlugin
from bigfoot.plugins.file_io_plugin import FileIoPlugin as FileIoPlugin
from bigfoot.plugins.logging_plugin import LoggingPlugin as LoggingPlugin
from bigfoot.plugins.memcache_plugin import MemcachePlugin as MemcachePlugin
from bigfoot.plugins.native_plugin import NativePlugin as NativePlugin
from bigfoot.plugins.popen_plugin import PopenPlugin as PopenPlugin
from bigfoot.plugins.redis_plugin import RedisPlugin as RedisPlugin
from bigfoot.plugins.smtp_plugin import SmtpPlugin as SmtpPlugin
from bigfoot.plugins.socket_plugin import SocketPlugin as SocketPlugin
from bigfoot.plugins.subprocess import SubprocessPlugin as SubprocessPlugin
from bigfoot.plugins.websocket_plugin import (
    AsyncWebSocketPlugin as AsyncWebSocketPlugin,
)
from bigfoot.plugins.websocket_plugin import (
    SyncWebSocketPlugin as SyncWebSocketPlugin,
)

# Optional plugin classes (may not be importable if extras not installed)
try:
    from bigfoot.plugins.http import HttpPlugin as HttpPlugin
except ImportError: ...

try:
    from bigfoot.plugins.celery_plugin import CeleryPlugin as CeleryPlugin
except ImportError: ...

try:
    from bigfoot.plugins.boto3_plugin import Boto3Plugin as Boto3Plugin
except ImportError: ...

try:
    from bigfoot.plugins.elasticsearch_plugin import (
        ElasticsearchPlugin as ElasticsearchPlugin,
    )
except ImportError: ...

try:
    from bigfoot.plugins.jwt_plugin import JwtPlugin as JwtPlugin
except ImportError: ...

try:
    from bigfoot.plugins.crypto_plugin import CryptoPlugin as CryptoPlugin
except ImportError: ...

try:
    from bigfoot.plugins.mongo_plugin import MongoPlugin as MongoPlugin
except ImportError: ...

try:
    from bigfoot.plugins.pika_plugin import PikaPlugin as PikaPlugin
except ImportError: ...

try:
    from bigfoot.plugins.ssh_plugin import SshPlugin as SshPlugin
except ImportError: ...

try:
    from bigfoot.plugins.grpc_plugin import GrpcPlugin as GrpcPlugin
except ImportError: ...

try:
    from bigfoot.plugins.mcp_plugin import McpPlugin as McpPlugin
except ImportError: ...

try:
    from bigfoot.plugins.psycopg2_plugin import Psycopg2Plugin as Psycopg2Plugin
except ImportError: ...

try:
    from bigfoot.plugins.asyncpg_plugin import AsyncpgPlugin as AsyncpgPlugin
except ImportError: ...

# ---------------------------------------------------------------------------
# Module-level context manager protocol
# ---------------------------------------------------------------------------

def __enter__() -> StrictVerifier: ...  # noqa: N807
def __exit__(  # noqa: N807
    __exc_type: type[BaseException] | None,
    __exc_val: BaseException | None,
    __exc_tb: types.TracebackType | None,
) -> None: ...
async def __aenter__() -> StrictVerifier: ...  # noqa: N807
async def __aexit__(  # noqa: N807
    __exc_type: type[BaseException] | None,
    __exc_val: BaseException | None,
    __exc_tb: types.TracebackType | None,
) -> None: ...

# ---------------------------------------------------------------------------
# Module-level functions
# ---------------------------------------------------------------------------

def current_verifier() -> StrictVerifier: ...
def sandbox() -> SandboxContext: ...
def assert_interaction(source: Any, **expected: object) -> None: ...  # noqa: ANN401
def in_any_order() -> InAnyOrderContext: ...
def verify_all() -> None: ...

# ---------------------------------------------------------------------------
# Module-level factories
# ---------------------------------------------------------------------------

class _MockFactory:
    def __call__(self, path: str) -> ImportSiteMock: ...
    def object(self, target: object, attr: str) -> ObjectMock: ...

class _SpyFactory:
    def __call__(self, path: str) -> ImportSiteMock: ...
    def object(self, target: object, attr: str) -> ObjectMock: ...

mock: _MockFactory
spy: _SpyFactory

# ---------------------------------------------------------------------------
# Plugin proxy singletons
# ---------------------------------------------------------------------------

http: Any  # HttpPlugin proxy; typed as Any because httpx/requests are optional
subprocess: Any  # SubprocessPlugin proxy
popen: Any  # PopenPlugin proxy
smtp: Any  # SmtpPlugin proxy
socket: Any  # SocketPlugin proxy
db: Any  # DatabasePlugin proxy
async_websocket: Any  # AsyncWebSocketPlugin proxy
sync_websocket: Any  # SyncWebSocketPlugin proxy
redis: Any  # RedisPlugin proxy
mongo: Any  # MongoPlugin proxy
dns: Any  # DnsPlugin proxy
memcache: Any  # MemcachePlugin proxy
celery: Any  # CeleryPlugin proxy
log: Any  # LoggingPlugin proxy
async_subprocess: Any  # AsyncSubprocessPlugin proxy
psycopg2: Any  # Psycopg2Plugin proxy
asyncpg: Any  # AsyncpgPlugin proxy
boto3: Any  # Boto3Plugin proxy
elasticsearch: Any  # ElasticsearchPlugin proxy
jwt: Any  # JwtPlugin proxy
crypto: Any  # CryptoPlugin proxy
file_io: Any  # FileIoPlugin proxy
pika: Any  # PikaPlugin proxy
ssh: Any  # SshPlugin proxy
grpc: Any  # GrpcPlugin proxy
mcp: Any  # McpPlugin proxy
native: Any  # NativePlugin proxy

# ---------------------------------------------------------------------------
# Deprecated ``_mock`` aliases (backward compatibility, scheduled for removal)
# ---------------------------------------------------------------------------
# Kept for type-checker compatibility so existing user code resolves. At runtime,
# accessing any of these names triggers a DeprecationWarning pointing at the new
# un-suffixed name. Use the canonical names above in new code.
subprocess_mock: Any  # Deprecated: use bigfoot.subprocess
popen_mock: Any  # Deprecated: use bigfoot.popen
smtp_mock: Any  # Deprecated: use bigfoot.smtp
socket_mock: Any  # Deprecated: use bigfoot.socket
db_mock: Any  # Deprecated: use bigfoot.db
async_websocket_mock: Any  # Deprecated: use bigfoot.async_websocket
sync_websocket_mock: Any  # Deprecated: use bigfoot.sync_websocket
redis_mock: Any  # Deprecated: use bigfoot.redis
mongo_mock: Any  # Deprecated: use bigfoot.mongo
dns_mock: Any  # Deprecated: use bigfoot.dns
memcache_mock: Any  # Deprecated: use bigfoot.memcache
celery_mock: Any  # Deprecated: use bigfoot.celery
log_mock: Any  # Deprecated: use bigfoot.log
async_subprocess_mock: Any  # Deprecated: use bigfoot.async_subprocess
psycopg2_mock: Any  # Deprecated: use bigfoot.psycopg2
asyncpg_mock: Any  # Deprecated: use bigfoot.asyncpg
boto3_mock: Any  # Deprecated: use bigfoot.boto3
elasticsearch_mock: Any  # Deprecated: use bigfoot.elasticsearch
jwt_mock: Any  # Deprecated: use bigfoot.jwt
crypto_mock: Any  # Deprecated: use bigfoot.crypto
file_io_mock: Any  # Deprecated: use bigfoot.file_io
pika_mock: Any  # Deprecated: use bigfoot.pika
ssh_mock: Any  # Deprecated: use bigfoot.ssh
grpc_mock: Any  # Deprecated: use bigfoot.grpc
mcp_mock: Any  # Deprecated: use bigfoot.mcp
native_mock: Any  # Deprecated: use bigfoot.native
