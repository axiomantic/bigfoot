# HttpPlugin Guide

`HttpPlugin` intercepts HTTP calls made through `httpx` (sync and async), `requests`, and `urllib`. It requires the `bigfoot[http]` extra.

## Installation

```bash
pip install bigfoot[http]
```

This installs `httpx>=0.25.0` and `requests>=2.31.0`.

## Setup

Construct `HttpPlugin` with a `StrictVerifier`. The plugin registers itself with the verifier:

```python
import httpx
from bigfoot import StrictVerifier
from bigfoot.plugins.http import HttpPlugin

verifier = StrictVerifier()
http = HttpPlugin(verifier)
```

Each verifier may have at most one `HttpPlugin`. A second `HttpPlugin(verifier)` raises `ValueError`.

## Registering mock responses

Use `http.mock_response(method, url, ...)` to register a response before entering the sandbox:

```python
http.mock_response("GET", "https://api.example.com/users", json={"users": []})
```

Parameters:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `method` | `str` | required | HTTP method, case-insensitive (`"GET"`, `"POST"`, etc.) |
| `url` | `str` | required | Full URL to match, including scheme and host |
| `json` | `object` | `None` | Response body serialized as JSON; sets `content-type: application/json` |
| `body` | `str \| bytes \| None` | `None` | Raw response body; mutually exclusive with `json` |
| `status` | `int` | `200` | HTTP status code |
| `headers` | `dict[str, str] \| None` | `None` | Additional response headers |
| `params` | `dict[str, str] \| None` | `None` | Query parameters that must be present in the request URL |
| `required` | `bool` | `True` | Whether an unused mock causes `UnusedMocksError` at teardown |

`json` and `body` are mutually exclusive; providing both raises `ValueError`.

## FIFO ordering

Multiple `mock_response()` calls for the same method+URL are consumed in registration order. The first matching request gets the first registered response, and so on. If a request arrives with no matching mock remaining, `UnmockedInteractionError` is raised.

```python
http.mock_response("GET", "https://api.example.com/token", json={"token": "first"})
http.mock_response("GET", "https://api.example.com/token", json={"token": "second"})
```

## Optional responses

Mark a mock response as optional with `required=False`:

```python
http.mock_response("GET", "https://api.example.com/health", json={"ok": True}, required=False)
```

An optional mock that is never triggered does not cause `UnusedMocksError` at teardown.

## URL matching

bigfoot matches on scheme, host, path, and (if `params` is provided) query parameters. Query parameters in the actual URL that are not listed in `params` are ignored.

```python
# Matches https://api.example.com/search?q=hello&page=2 if params={"q": "hello"}
http.mock_response("GET", "https://api.example.com/search", json={...}, params={"q": "hello"})
```

## Asserting HTTP interactions

Use `http.request` as the source in `assert_interaction()`. The `http.request` property returns an `HttpRequestSentinel` with `source_id = "http:request"`.

```python
with verifier.sandbox():
    response = httpx.get("https://api.example.com/users")

verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/users", status=200)
verifier.verify_all()
```

Fields available in `assert_interaction()` keyword arguments:

| Field | Description |
|---|---|
| `method` | HTTP method, uppercase |
| `url` | Full URL as received |
| `headers` | Request headers dict |
| `body` | Request body decoded as UTF-8 |
| `status` | Response status code |

## Using with httpx sync

```python
import httpx

http.mock_response("GET", "https://api.example.com/data", json={"value": 42})

with verifier.sandbox():
    response = httpx.get("https://api.example.com/data")
    assert response.status_code == 200
    assert response.json() == {"value": 42}

verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/data")
verifier.verify_all()
```

## Using with httpx async

```python
import httpx

http.mock_response("POST", "https://api.example.com/items", json={"id": 1}, status=201)

async with verifier.sandbox():
    async with httpx.AsyncClient() as client:
        response = await client.post("https://api.example.com/items", json={"name": "widget"})
    assert response.status_code == 201

verifier.assert_interaction(http.request, method="POST", url="https://api.example.com/items", status=201)
verifier.verify_all()
```

## Using with requests

```python
import requests

http.mock_response("DELETE", "https://api.example.com/items/99", status=204)

with verifier.sandbox():
    response = requests.delete("https://api.example.com/items/99")
    assert response.status_code == 204

verifier.assert_interaction(http.request, method="DELETE", url="https://api.example.com/items/99", status=204)
verifier.verify_all()
```

## UnmockedInteractionError for HTTP

When HTTP code fires a request with no matching mock, bigfoot raises `UnmockedInteractionError` with a hint:

```
Unexpected HTTP request: GET https://api.example.com/data

  To mock this request, add before your sandbox:
    http.mock_response("GET", "https://api.example.com/data", json={...})

  Or to mark it optional:
    http.mock_response("GET", "https://api.example.com/data", json={...}, required=False)
```

## ConflictError

At sandbox entry, `HttpPlugin` checks whether `httpx.HTTPTransport.handle_request`, `httpx.AsyncHTTPTransport.handle_async_request`, and `requests.adapters.HTTPAdapter.send` have already been patched by another library. If any of these have been modified by a third party (respx, responses, httpretty, or an unknown library), bigfoot raises `ConflictError`:

```
ConflictError: target='httpx.HTTPTransport.handle_request', patcher='respx'
```

Nested bigfoot sandboxes use reference counting and do not conflict with each other.

## What HttpPlugin patches

When the sandbox activates, `HttpPlugin` installs class-level patches on:

- `httpx.HTTPTransport.handle_request` (sync httpx)
- `httpx.AsyncHTTPTransport.handle_async_request` (async httpx)
- `requests.adapters.HTTPAdapter.send` (requests library)
- `urllib.request` opener (urllib)
- `asyncio.BaseEventLoop.run_in_executor` (propagates ContextVar to thread pool executors)

All patches are reference-counted. Nested sandboxes increment/decrement the count; the actual method replacement only happens at count transitions from 0 to 1 and from 1 to 0.

The `run_in_executor` patch ensures the active-verifier `ContextVar` is copied into threads spawned by `asyncio.run_in_executor`, so HTTP calls made from thread pools are intercepted correctly.
