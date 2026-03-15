# bigfoot

**bigfoot** intercepts every external call your code makes and forces your tests to account for all of them. It enforces three guarantees that most mocking libraries leave silent:

1. **Every call must be pre-authorized.** If code makes a call with no registered mock, bigfoot raises `UnmockedInteractionError` immediately at call time.
2. **Every recorded interaction must be explicitly asserted.** At teardown, any interaction not passed to an assertion method causes `UnassertedInteractionsError`.
3. **Every registered mock must actually be triggered.** At teardown, any mock registered with `required=True` (the default) but never called causes `UnusedMocksError`.

Standard mocking libraries let tests pass silently when a mock is registered for an endpoint that the code never calls, when a side-effecting call is intercepted but the test never checks that it happened, or when a mock is configured with wrong arguments and the code hits a different mock. bigfoot makes each of these conditions a hard test failure.

## Quick example

```python
import bigfoot
from dirty_equals import IsInstance

def create_charge(amount):
    """Production code -- calls Stripe via httpx internally."""
    import httpx
    response = httpx.post("https://api.stripe.com/v1/charges",
                          json={"amount": amount})
    return response.json()

def test_payment_flow():
    bigfoot.http.mock_response("POST", "https://api.stripe.com/v1/charges",
                               json={"id": "ch_123"}, status=200)

    with bigfoot:
        result = create_charge(5000)

    bigfoot.http.assert_request(
        "POST", "https://api.stripe.com/v1/charges",
        headers=IsInstance(dict), body='{"amount": 5000}',
    )
    assert result["id"] == "ch_123"
```

The test calls `create_charge()`, which internally uses httpx. bigfoot intercepts the HTTP call transparently. If you forget the `assert_request()` call, bigfoot raises `UnassertedInteractionsError` at teardown. If the mock is never triggered, `UnusedMocksError`. If code makes an unmocked HTTP call, `UnmockedInteractionError` immediately.

## Navigation

<div class="grid cards" markdown>

- **[Installation](guides/installation.md)**

    Install bigfoot and its optional extras.

- **[Quick Start](guides/quickstart.md)**

    A complete walkthrough from setup to teardown.

- **[MockPlugin Guide](guides/mock-plugin.md)**

    Full reference for configuring method mocks, FIFO queues, and in-any-order assertions.

- **[HttpPlugin Guide](guides/http-plugin.md)**

    Intercept httpx, requests, and urllib HTTP calls in tests.

- **[SubprocessPlugin Guide](guides/subprocess-plugin.md)**

    Intercept `subprocess.run` and `shutil.which` in tests.

</div>
