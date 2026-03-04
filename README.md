# panoptest

A pluggable interaction auditor for Python tests. Enforces a closed-loop contract:

- **Bouncer**: Every external interaction must be pre-authorized. Unmocked calls raise `UnmockedInteractionError` immediately.
- **Auditor**: Every recorded interaction must be explicitly asserted. Unasserted interactions raise `UnassertedInteractionsError` at teardown.
- **Accountant**: Every registered mock must be triggered. Unused mocks raise `UnusedMocksError` at teardown.

## Installation

```bash
pip install panoptest           # Core: MockPlugin
pip install panoptest[http]     # + HttpPlugin (httpx, requests, urllib)
pip install panoptest[matchers] # + dirty-equals matchers
pip install panoptest[dev]      # All of the above + pytest, mypy, ruff
```

## Quick Start

```python
import httpx
from panoptest.plugins.http import HttpPlugin

def test_payment_flow(panoptest_verifier):
    http = HttpPlugin(panoptest_verifier)
    http.mock_response("POST", "https://api.stripe.com/v1/charges",
                       json={"id": "ch_123"}, status=200)

    with panoptest_verifier.sandbox():
        response = httpx.post("https://api.stripe.com/v1/charges",
                              json={"amount": 5000})
        panoptest_verifier.assert_interaction(
            http.request,
            method="POST",
            url="https://api.stripe.com/v1/charges",
        )

    assert response.json()["id"] == "ch_123"
    # verify_all() called automatically by panoptest_verifier fixture
```

## Mock Plugin

```python
def test_service_calls(panoptest_verifier):
    payment = panoptest_verifier.mock("PaymentService")
    payment.charge.returns({"status": "ok"})
    payment.refund.required(False).returns(None)  # optional mock

    with panoptest_verifier.sandbox():
        result = payment.charge(order_id=42)
        panoptest_verifier.assert_interaction(payment.charge)
```

The `mock()` shorthand on `StrictVerifier` lazily creates a `MockPlugin` on first use. For explicit control:

```python
from panoptest import StrictVerifier, MockPlugin

verifier = StrictVerifier()
mock_plugin = MockPlugin(verifier)
proxy = mock_plugin.get_or_create_proxy("MyService")
proxy.fetch.returns({"data": []})
```

### Side Effects

```python
proxy.compute.returns(42)                   # Return a value
proxy.compute.returns(1).returns(2)         # FIFO: first call returns 1, second returns 2
proxy.fetch.raises(IOError("unavailable"))  # Raise an exception
proxy.transform.calls(lambda x: x.upper()) # Delegate to a function
proxy.log.required(False).returns(None)     # Optional: no UnusedMocksError if never called
```

## Async Tests

The `panoptest_verifier` fixture and `sandbox()` context manager both support async:

```python
async def test_async_flow(panoptest_verifier):
    http = HttpPlugin(panoptest_verifier)
    http.mock_response("GET", "https://api.example.com/items", json=[])

    async with panoptest_verifier.sandbox():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/items")
        panoptest_verifier.assert_interaction(http.request, method="GET")
```

## Concurrent Assertions

When tests make concurrent HTTP requests (e.g., via `asyncio.TaskGroup`), use `in_any_order()` to relax the FIFO ordering requirement:

```python
async def test_concurrent(panoptest_verifier):
    http = HttpPlugin(panoptest_verifier)
    http.mock_response("GET", "https://api.example.com/a", json={"a": 1})
    http.mock_response("GET", "https://api.example.com/b", json={"b": 2})

    async with panoptest_verifier.sandbox():
        # ... make concurrent requests ...

    with panoptest_verifier.in_any_order():
        panoptest_verifier.assert_interaction(http.request, url="https://api.example.com/a")
        panoptest_verifier.assert_interaction(http.request, url="https://api.example.com/b")
```

`in_any_order()` operates globally across all plugin types (mock and HTTP).

## pytest Integration

The `panoptest_verifier` fixture is registered automatically via the `pytest11` entry point. No import required:

```python
def test_something(panoptest_verifier):
    ...
    # verify_all() runs at teardown automatically
```

## HTTP Interception Scope

`HttpPlugin` intercepts at the transport/adapter level:

- `httpx.Client` and `httpx.AsyncClient` (class-level transport patch)
- `requests.get()`, `requests.Session`, etc. (class-level adapter patch)
- `urllib.request.urlopen()` (via `install_opener`)

Not intercepted: `httpx.ASGITransport`, `httpx.WSGITransport`, `aiohttp`.

## Error Messages

panoptest errors include copy-pasteable remediation hints:

```
UnmockedInteractionError: source_id='mock:PaymentService.charge', args=('order_42',), kwargs={},
hint='Unexpected call to PaymentService.charge

  Called with: args=('order_42',), kwargs={}

  To mock this interaction, add before your sandbox:
    verifier.mock("PaymentService").charge.returns(<value>)

  Or to mark it optional:
    verifier.mock("PaymentService").charge.required(False).returns(<value>)'
```

## Public API

```python
from panoptest import (
    StrictVerifier,
    SandboxContext,
    InAnyOrderContext,
    MockPlugin,
    PanoptestError,
    UnmockedInteractionError,
    UnassertedInteractionsError,
    UnusedMocksError,
    VerificationError,
    InteractionMismatchError,
    SandboxNotActiveError,
    ConflictError,
)
from panoptest.plugins.http import HttpPlugin  # requires panoptest[http]
```

## Requirements

- Python 3.11+
- pytest (for `panoptest_verifier` fixture)

## License

MIT
