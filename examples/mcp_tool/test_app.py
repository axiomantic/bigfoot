"""Test MCP tool call using bigfoot mcp."""

import pytest

import bigfoot

from .app import fetch_weather


@pytest.mark.asyncio
async def test_fetch_weather():
    from mcp.client.session import ClientSession

    bigfoot.mcp.mock_call_tool(
        "get_weather",
        returns={"content": [{"type": "text", "text": "Sunny, 72F"}]},
    )

    with bigfoot:
        session = object.__new__(ClientSession)
        result = await fetch_weather(session, "San Francisco")

    assert result == {"content": [{"type": "text", "text": "Sunny, 72F"}]}

    bigfoot.mcp.assert_call_tool(
        "get_weather",
        arguments={"city": "San Francisco"},
        direction="client",
    )
