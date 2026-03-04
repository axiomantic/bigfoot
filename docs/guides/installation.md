# Installation

## Core

Install the core package with pip:

```bash
pip install bigfoot
```

The core package includes `StrictVerifier`, `MockPlugin`, and the pytest fixture. It has no runtime dependencies beyond Python 3.11+.

## HTTP interception

To intercept `httpx`, `requests`, and `urllib` HTTP calls, install the `http` extra:

```bash
pip install bigfoot[http]
```

This installs `httpx>=0.25.0` and `requests>=2.31.0` alongside `HttpPlugin`.

## Matcher support

To use [dirty-equals](https://dirty-equals.helpmanual.io/) matchers in `assert_interaction()` field comparisons:

```bash
pip install bigfoot[matchers]
```

This installs `dirty-equals>=0.7.0`. Once installed, you can pass dirty-equals expressions as expected field values and bigfoot's `matches()` logic will use their `__eq__` implementations.

## All extras

```bash
pip install bigfoot[http,matchers]
```

## pytest fixture

The `bigfoot_verifier` pytest fixture is registered automatically via the `pytest11` entry point. No `conftest.py` changes are needed. Install bigfoot and the fixture is available in any pytest session:

```python
def test_example(bigfoot_verifier):
    # bigfoot_verifier is a StrictVerifier with automatic verify_all() at teardown
    ...
```
