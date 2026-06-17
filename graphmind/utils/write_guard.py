"""Gate write operations until the user explicitly confirms."""
from __future__ import annotations

import json
import os

WRITE_METHODS = frozenset({"POST", "PATCH", "PUT", "DELETE"})


def is_write_confirmation_required() -> bool:
    return os.getenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "true").lower() in (
        "1",
        "true",
        "yes",
    )


def is_write_method(method: str) -> bool:
    return method.upper() in WRITE_METHODS


def _action_label(path: str) -> str:
    segment = path.rstrip("/").split("/")[-1].split("(", 1)[0]
    if segment.startswith("$") or segment.startswith("{"):
        return "write operation"
    return segment.replace("-", " ")


def build_confirmation_request(
    *,
    method: str,
    path: str,
    api_version: str,
    api_type: str = "graph",
    query_params: dict | None = None,
    body: dict | None = None,
) -> str:
    action = _action_label(path)
    lines = [
        "⚠️ **Confirmation required** — this is a write operation that changes tenant state.",
        "",
        f"**Action:** {action}",
        f"**Request:** {method.upper()} /{api_version}{path}",
        f"**API:** {api_type}",
    ]
    if query_params:
        lines.append(f"**Query params:** `{json.dumps(query_params, default=str)}`")
    if body:
        lines.append(f"**Body:** `{json.dumps(body, default=str)}`")
    lines.extend(
        [
            "",
            "Ask the user to confirm before proceeding. If they approve, call `call_graph_api` "
            "again with the **same parameters** and `confirmed: true`.",
            "If they decline, do not call the API.",
        ]
    )
    return "\n".join(lines)
