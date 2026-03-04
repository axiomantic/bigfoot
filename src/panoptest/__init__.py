"""panoptest: a pluggable interaction auditor for Python tests."""

from panoptest._errors import (
    ConflictError,
    InteractionMismatchError,
    PanoptestError,
    SandboxNotActiveError,
    UnassertedInteractionsError,
    UnmockedInteractionError,
    UnusedMocksError,
    VerificationError,
)
from panoptest._mock_plugin import MockPlugin
from panoptest._verifier import InAnyOrderContext, SandboxContext, StrictVerifier

try:
    from panoptest.plugins.http import HttpPlugin  # noqa: F401
except ImportError:  # pragma: no cover
    pass  # http extra not installed

__all__ = [
    "StrictVerifier",
    "SandboxContext",
    "InAnyOrderContext",
    "MockPlugin",
    "PanoptestError",
    "UnmockedInteractionError",
    "UnassertedInteractionsError",
    "UnusedMocksError",
    "VerificationError",
    "InteractionMismatchError",
    "SandboxNotActiveError",
    "ConflictError",
]
