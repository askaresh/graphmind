import asyncio
from unittest.mock import patch

import pytest


def test_server_imports():
    import graphmind.mcp.server  # noqa: F401


def test_read_only_blocks_writes(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "true")
    monkeypatch.setenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "false")
    from graphmind.mcp.server import _call

    async def run():
        return await _call({"path": "/users", "method": "POST"})

    result = asyncio.run(run())
    assert "read-only mode" in result[0].text.lower()


def test_write_requires_confirmation(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "false")
    monkeypatch.setenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "true")
    from graphmind.mcp.server import _call

    async def run():
        with patch("graphmind.mcp.server.call_graph") as mock_call:
            result = await _call(
                {
                    "path": "/deviceManagement/virtualEndpoint/cloudPCs/abc/reboot",
                    "method": "POST",
                }
            )
            return result, mock_call

    result, mock_call = asyncio.run(run())
    assert "Confirmation required" in result[0].text
    mock_call.assert_not_called()


def test_write_executes_when_confirmed(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "false")
    monkeypatch.setenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "true")
    from graphmind.mcp.server import _call

    async def run():
        with patch("graphmind.mcp.server.call_graph") as mock_call:
            mock_call.return_value = {"ok": True, "status_code": 204, "data": {}}
            return await _call(
                {
                    "path": "/deviceManagement/virtualEndpoint/cloudPCs/abc/reboot",
                    "method": "POST",
                    "confirmed": True,
                }
            )

    result = asyncio.run(run())
    assert result[0].text.startswith("✅")


def test_write_skips_confirmation_when_disabled(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "false")
    monkeypatch.setenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "false")
    from graphmind.mcp.server import _call

    async def run():
        with patch("graphmind.mcp.server.call_graph") as mock_call:
            mock_call.return_value = {"ok": True, "status_code": 204, "data": {}}
            return await _call(
                {
                    "path": "/deviceManagement/virtualEndpoint/cloudPCs/abc/reboot",
                    "method": "POST",
                }
            )

    result = asyncio.run(run())
    assert result[0].text.startswith("✅")


def test_read_only_allows_get(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "false")
    from graphmind.mcp.server import _call

    async def run():
        with patch("graphmind.mcp.server.call_graph") as mock_call:
            mock_call.return_value = {"ok": True, "status_code": 200, "data": {"value": []}}
            return await _call({"path": "/users", "method": "GET"})

    result = asyncio.run(run())
    assert result[0].text.startswith("✅")


def test_call_404_suggests_alternates(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_READ_ONLY", "false")
    from graphmind.mcp.server import _call
    from graphmind.spec.loader import Endpoint

    retrieve = Endpoint(
        path="/deviceManagement/virtualEndpoint/cloudPCs/{cloudPC-id}/retrieveSnapshots()",
        method="GET",
        api_version="beta",
        operation_id="retrieveSnapshots",
        summary="Invoke function retrieveSnapshots",
        description="List snapshots for a Cloud PC",
        tags=["deviceManagement.virtualEndpoint"],
        parameters=[],
        request_body=None,
        permissions=[],
        deprecated=False,
    )

    async def run():
        with patch("graphmind.mcp.server.call_graph") as mock_call, patch(
            "graphmind.mcp.server.get_index"
        ) as mock_index:
            mock_call.return_value = {
                "ok": False,
                "status_code": 404,
                "data": {"error": {"code": "UnknownError", "message": "Not found"}},
                "error": {"code": "UnknownError", "message": "Not found"},
            }
            mock_index.return_value.beta = [retrieve]
            mock_index.return_value.v1 = []
            return await _call(
                {
                    "path": "/deviceManagement/virtualEndpoint/snapshots",
                    "method": "GET",
                    "api_version": "beta",
                }
            )

    result = asyncio.run(run())
    assert "retrieveSnapshots" in result[0].text
