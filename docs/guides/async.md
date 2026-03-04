# Async Usage

bigfoot supports async tests natively. `SandboxContext` and `InAnyOrderContext` both implement `__aenter__` and `__aexit__`.

## async with sandbox

Use `async with verifier.sandbox()` in an async test function:

```python
import httpx
import pytest
from bigfoot import StrictVerifier
from bigfoot.plugins.http import HttpPlugin

@pytest.mark.asyncio
async def test_async_http():
    verifier = StrictVerifier()
    http = HttpPlugin(verifier)
    http.mock_response("GET", "https://api.example.com/data", json={"ok": True})

    async with verifier.sandbox():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/data")
        assert response.json() == {"ok": True}

    verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/data")
    verifier.verify_all()
```

The sync and async forms are equivalent. `SandboxContext._enter()` and `_exit()` are synchronous under the hood; the async wrapper simply delegates to them.

## ContextVar isolation

The active verifier is stored in a `contextvars.ContextVar`. Each `asyncio.create_task()` call inherits a copy of the current context, so concurrent tasks see the correct verifier without interference:

```python
import asyncio
import httpx
from bigfoot import StrictVerifier
from bigfoot.plugins.http import HttpPlugin

async def fetch(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
    return response.json()

async def test_concurrent_requests():
    verifier = StrictVerifier()
    http = HttpPlugin(verifier)
    http.mock_response("GET", "https://api.example.com/a", json={"name": "a"})
    http.mock_response("GET", "https://api.example.com/b", json={"name": "b"})

    async with verifier.sandbox():
        a, b = await asyncio.gather(
            asyncio.create_task(fetch("https://api.example.com/a")),
            asyncio.create_task(fetch("https://api.example.com/b")),
        )

    with verifier.in_any_order():
        verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/a")
        verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/b")

    verifier.verify_all()
```

Because concurrent tasks may complete in any order, use `verifier.in_any_order()` when asserting interactions from concurrent work.

## async with in_any_order

`InAnyOrderContext` also supports `async with`:

```python
async with verifier.in_any_order():
    verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/a")
    verifier.assert_interaction(http.request, method="GET", url="https://api.example.com/b")
```

## run_in_executor propagation

When `HttpPlugin` is active, bigfoot patches `asyncio.BaseEventLoop.run_in_executor` to copy the current `contextvars` context into the thread pool executor. This means HTTP calls made from a thread via `run_in_executor` are intercepted by the correct verifier:

```python
import asyncio
import urllib.request

async def fetch_in_thread(url: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: urllib.request.urlopen(url).read())

async def test_thread_pool_interception():
    verifier = StrictVerifier()
    http = HttpPlugin(verifier)
    http.mock_response("GET", "https://api.example.com/data", body=b"hello")

    async with verifier.sandbox():
        data = await fetch_in_thread("https://api.example.com/data")
        assert data == b"hello"

    verifier.assert_interaction(http.request, method="GET")
    verifier.verify_all()
```

Without this patch, the thread would not inherit the ContextVar and would see no active sandbox.

## MockPlugin with async tests

`MockPlugin` works identically in async tests. No special async API is needed because mock calls are synchronous intercepts:

```python
async def test_async_mock():
    verifier = StrictVerifier()
    repo = verifier.mock("UserRepository")
    repo.find_by_id.returns({"id": 1, "name": "Alice"})

    async with verifier.sandbox():
        user = repo.find_by_id(1)
        assert user["name"] == "Alice"

    verifier.assert_interaction(repo.find_by_id)
    verifier.verify_all()
```
