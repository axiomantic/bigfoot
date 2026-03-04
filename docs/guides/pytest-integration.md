# pytest Integration

bigfoot ships with a pytest fixture that provides a `StrictVerifier` with automatic teardown verification.

## The bigfoot_verifier fixture

The `bigfoot_verifier` fixture is registered automatically via the `pytest11` entry point. No `conftest.py` changes are required. Install bigfoot and the fixture is immediately available:

```python
from bigfoot import StrictVerifier

def test_example(bigfoot_verifier: StrictVerifier):
    email = bigfoot_verifier.mock("EmailService")
    email.send.returns(True)

    with bigfoot_verifier.sandbox():
        email.send(to="user@example.com")

    bigfoot_verifier.assert_interaction(email.send)
    # verify_all() is called automatically at teardown
```

The fixture:

1. Creates a `StrictVerifier`
2. Registers a finalizer that calls `verifier.verify_all()` after the test completes
3. Returns the verifier

The sandbox is **not** automatically activated. The test controls when to enter and exit the sandbox.

## Async tests

The `bigfoot_verifier` fixture works with async tests. Use `pytest-asyncio` and `async with`:

```python
import httpx
import pytest
from bigfoot.plugins.http import HttpPlugin

@pytest.mark.asyncio
async def test_async_http(bigfoot_verifier):
    http = HttpPlugin(bigfoot_verifier)
    http.mock_response("GET", "https://api.example.com/items", json={"items": []})

    async with bigfoot_verifier.sandbox():
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.example.com/items")
        assert response.json() == {"items": []}

    bigfoot_verifier.assert_interaction(http.request, method="GET")
    # verify_all() called at teardown
```

## Using HttpPlugin with the fixture

Construct `HttpPlugin` inside the test, passing `bigfoot_verifier` as the verifier:

```python
import requests
from bigfoot.plugins.http import HttpPlugin

def test_api_call(bigfoot_verifier):
    http = HttpPlugin(bigfoot_verifier)
    http.mock_response("POST", "https://api.example.com/users", json={"id": 42}, status=201)

    with bigfoot_verifier.sandbox():
        response = requests.post("https://api.example.com/users", json={"name": "Alice"})
        assert response.status_code == 201
        assert response.json()["id"] == 42

    bigfoot_verifier.assert_interaction(
        http.request,
        method="POST",
        url="https://api.example.com/users",
        status=201,
    )
```

## Teardown behavior

`verify_all()` is called via `request.addfinalizer()`. This runs after the test function returns (or raises), so if your test fails with an assertion error mid-way, `verify_all()` still runs. If both the test assertion and `verify_all()` fail, pytest reports both errors.

## Manual StrictVerifier

If you need more control, create `StrictVerifier` manually and call `verify_all()` yourself:

```python
from bigfoot import StrictVerifier

def test_manual():
    verifier = StrictVerifier()
    try:
        email = verifier.mock("EmailService")
        email.send.returns(True)

        with verifier.sandbox():
            email.send(to="user@example.com")

        verifier.assert_interaction(email.send)
    finally:
        verifier.verify_all()
```

The `try/finally` ensures `verify_all()` runs even if assertions fail, which mirrors what the fixture does.
