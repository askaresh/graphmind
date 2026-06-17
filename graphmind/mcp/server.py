"""
mcp/server.py — GraphMind MCP Server
Four tools: search_graph_api | get_endpoint_schema | get_changelog | call_graph_api
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..auth.token import get_granted_permissions
from ..reranker.cross_encoder import rerank
from ..spec.filter import FilterIntent, apply_structural_filter
from ..spec.loader import get_index, load_index
from ..spec.query_hints import infer_search_hints, suggest_alternate_endpoints
from ..utils.graph_client import call_azure, call_graph
from ..utils.pagination import DEFAULT_MAX_PAGES, DEFAULT_SAMPLE_SIZE, paginate_graph
from ..utils.write_guard import (
    build_confirmation_request,
    is_write_confirmation_required,
    is_write_method,
)

load_dotenv()

RERANKER_TOP_K = int(os.getenv("RERANKER_TOP_K", "20"))
DEFAULT_API_VERSION = os.getenv("DEFAULT_API_VERSION", "v1.0")
MAX_RESPONSE_CHARS = int(os.getenv("GRAPHMIND_MAX_RESPONSE_CHARS", "8000"))
DECOMMISSION_LOG = Path("./graphmind_decommission_log.jsonl")
PROMOTION_LOG = Path("./graphmind_promotion_log.json")

app = Server(os.getenv("MCP_SERVER_NAME", "graphmind"))

_index_lock = asyncio.Lock()
_index_ready = False
_index_loading = False


async def _ensure_index():
    """Load the spec index on first use (non-blocking for MCP handshake)."""
    global _index_ready, _index_loading
    if _index_ready:
        return
    async with _index_lock:
        if _index_ready:
            return
        if _index_loading:
            while not _index_ready:
                await asyncio.sleep(0.5)
            return
        _index_loading = True
        repo_path = os.getenv("SPEC_REPO_PATH", "./msgraph-metadata")
        print(f"GraphMind: loading spec index from {repo_path}...", file=sys.stderr, flush=True)
        loop = asyncio.get_running_loop()
        try:
            await loop.run_in_executor(
                None,
                lambda: load_index(repo_path, required=True, quiet=True),
            )
            idx = get_index()
            print(
                f"GraphMind: index ready ({idx.total:,} endpoints).",
                file=sys.stderr,
                flush=True,
            )
            _index_ready = True
        finally:
            _index_loading = False


def _is_read_only() -> bool:
    return os.getenv("GRAPHMIND_READ_ONLY", "false").lower() in ("1", "true", "yes")


def _load_promotions() -> dict:
    if PROMOTION_LOG.exists():
        return json.loads(PROMOTION_LOG.read_text(encoding="utf-8"))
    return {}


def _trust_label(ep) -> str:
    if ep.api_version == "v1.0":
        return "✅ Stable (v1.0)"
    promotions = _load_promotions()
    if ep.chunk_id in promotions:
        v1_path = promotions[ep.chunk_id]
        return f"⬆️ Beta (graduated to v1.0 at {v1_path} — consider switching)"
    return "⚠️ Beta (subject to change — not supported in production by Microsoft)"


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    read_only_note = " Read-only mode is enabled — write methods are blocked." if _is_read_only() else ""
    return [
        types.Tool(
            name="search_graph_api",
            description=(
                "Search the local Microsoft Graph API index via 3-tier funnel: "
                "structural filter → cross-encoder rerank → full schema injection. "
                "Defaults to v1.0 (stable). Set api_version='beta' for cutting-edge features. "
                "Always call this BEFORE call_graph_api."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural language — what do you want to do?"},
                    "api_version": {
                        "type": "string",
                        "enum": ["beta", "v1.0", "both"],
                        "default": "v1.0",
                        "description": "v1.0 = stable (default). beta = latest features. both = search all.",
                    },
                    "method": {"type": "string", "enum": ["GET", "POST", "PATCH", "PUT", "DELETE"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "keyword": {"type": "string"},
                    "filter_by_permissions": {"type": "boolean", "default": True},
                    "fallback_to_v1": {
                        "type": "boolean",
                        "default": True,
                        "description": "If beta returns no results, automatically search v1.0",
                    },
                },
                "required": ["query"],
            },
        ),
        types.Tool(
            name="get_endpoint_schema",
            description="Full parameter schema for a known endpoint.",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "method": {"type": "string"},
                    "api_version": {"type": "string", "default": "v1.0"},
                },
                "required": ["path", "method"],
            },
        ),
        types.Tool(
            name="get_changelog",
            description="List recently decommissioned Graph API endpoints.",
            inputSchema={
                "type": "object",
                "properties": {"days": {"type": "integer", "default": 14}},
            },
        ),
        types.Tool(
            name="call_graph_api",
            description=(
                "Execute an authenticated call against Microsoft Graph or Azure RM. "
                "ALWAYS call search_graph_api first. "
                "For large collections (e.g. thousands of users), set paginate=true and "
                "aggregate=true to auto-page and return a count + sample instead of raw JSON. "
                "Write methods (POST/PATCH/PUT/DELETE) require user confirmation: first call "
                "returns a preview; re-call with confirmed=true after the user approves."
                + read_only_note
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "api_type": {"type": "string", "enum": ["graph", "azure"], "default": "graph"},
                    "path": {"type": "string"},
                    "method": {"type": "string", "default": "GET"},
                    "api_version": {
                        "type": "string",
                        "default": "v1.0",
                        "description": "beta or v1.0 — determines the URL prefix used",
                    },
                    "query_params": {"type": "object"},
                    "body": {"type": "object"},
                    "paginate": {
                        "type": "boolean",
                        "default": False,
                        "description": "Follow @odata.nextLink until max_pages (Graph GET collections only)",
                    },
                    "max_pages": {
                        "type": "integer",
                        "default": DEFAULT_MAX_PAGES,
                        "description": "Max pages when paginate=true (999 items/page typical)",
                    },
                    "aggregate": {
                        "type": "boolean",
                        "default": True,
                        "description": "When paginate=true, return total count + sample instead of full list",
                    },
                    "sample_size": {
                        "type": "integer",
                        "default": DEFAULT_SAMPLE_SIZE,
                        "description": "Sample rows when aggregate=true",
                    },
                    "confirmed": {
                        "type": "boolean",
                        "default": False,
                        "description": (
                            "Required for POST/PATCH/PUT/DELETE. Leave false on the first call "
                            "to get a confirmation preview; set true only after the user approves."
                        ),
                    },
                },
                "required": ["path"],
            },
        ),
    ]


@app.call_tool()
async def handle_tool(name: str, arguments: dict) -> list[types.TextContent]:
    await _ensure_index()
    if name == "search_graph_api":
        return await _search(arguments)
    if name == "get_endpoint_schema":
        return await _schema(arguments)
    if name == "get_changelog":
        return await _changelog(arguments)
    if name == "call_graph_api":
        return await _call(arguments)
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]


async def _search(args: dict) -> list[types.TextContent]:
    query = args.get("query", "")
    api_version = args.get("api_version", DEFAULT_API_VERSION)
    fallback = args.get("fallback_to_v1", True)
    granted = get_granted_permissions() if args.get("filter_by_permissions", True) else None

    hints = infer_search_hints(
        query,
        api_version=api_version,
        tags=args.get("tags") or None,
        keyword=args.get("keyword"),
    )
    beta_auto = False
    if hints.prefer_beta:
        api_version = "beta"
        beta_auto = True

    intent = FilterIntent(
        api_version=api_version,
        method=args.get("method"),
        tags=hints.tags or None,
        keyword=args.get("keyword"),
        keywords=hints.keywords or None,
        exclude_deprecated=True,
        granted_permissions=granted,
    )
    filter_result = apply_structural_filter(intent)
    candidates = filter_result.endpoints
    truncated = filter_result.truncated

    fallback_used = False
    if not candidates and api_version == "beta" and fallback:
        intent.api_version = "v1.0"
        filter_result = apply_structural_filter(intent)
        candidates = filter_result.endpoints
        truncated = filter_result.truncated
        fallback_used = True
        beta_auto = False

    if not candidates:
        return [
            types.TextContent(
                type="text",
                text="No endpoints found. Try: broader tags, different keywords, or api_version='both'.",
            )
        ]

    top = rerank(query, candidates, top_k=RERANKER_TOP_K) if len(candidates) > RERANKER_TOP_K else candidates

    promotions = _load_promotions()
    schemas = []
    for ep in top:
        schema = ep.to_full_schema()
        if "()" in ep.path:
            schema += (
                "\n\n> 💡 **OData function** — append `()` to the URL "
                "(e.g. `.../cloudPCs/{id}/retrieveSnapshots()`)."
            )
        if ep.chunk_id in promotions:
            v1_path = promotions[ep.chunk_id]
            schema += (
                f"\n\n> 💡 **This beta endpoint graduated to v1.0**: `{v1_path}` "
                "— use v1.0 for production."
            )
        schemas.append(f"{_trust_label(ep)}\n{schema}")

    header = ""
    if beta_auto:
        header = "ℹ️ Cloud PC / snapshot query — auto-selected api_version='beta' (beta-only APIs).\n\n"
    if fallback_used:
        header = "ℹ️ No beta results found — showing v1.0 results instead.\n\n"
    if truncated:
        header += (
            f"⚠️ Structural filter hit ceiling ({filter_result.total_before_ceiling:,} → "
            f"{len(candidates):,}). Add tags or keyword to narrow results.\n\n"
        )

    text = (
        f"{header}Structural filter: {len(candidates):,} candidates → top {len(top)} reranked "
        f"(source: {'v1.0 fallback' if fallback_used else api_version}).\n\n"
        + "\n\n---\n\n".join(schemas)
    )
    return [types.TextContent(type="text", text=text)]


async def _schema(args: dict) -> list[types.TextContent]:
    path = args.get("path", "")
    method = args.get("method", "GET").upper()
    api_version = args.get("api_version", DEFAULT_API_VERSION)
    chunk_id = hashlib.sha256(f"{api_version}::{path}::{method}".encode()).hexdigest()[:16]
    ep = get_index().get_by_id(chunk_id)
    if not ep:
        alt_version = "v1.0" if api_version == "beta" else "beta"
        alt_id = hashlib.sha256(f"{alt_version}::{path}::{method}".encode()).hexdigest()[:16]
        ep = get_index().get_by_id(alt_id)
        if ep:
            return [
                types.TextContent(
                    type="text",
                    text=(
                        f"Not found in {api_version}, but exists in {alt_version}:\n\n"
                        f"{_trust_label(ep)}\n{ep.to_full_schema()}"
                    ),
                )
            ]
        return [
            types.TextContent(
                type="text",
                text=f"Not found in local index: {method} {path} ({api_version}). May be brand-new.",
            )
        ]
    return [types.TextContent(type="text", text=f"{_trust_label(ep)}\n{ep.to_full_schema()}")]


async def _changelog(args: dict) -> list[types.TextContent]:
    days = int(args.get("days", 14))
    since = date.today() - timedelta(days=days)
    if not DECOMMISSION_LOG.exists():
        return [types.TextContent(type="text", text="No decommission log yet. Run: graphmind refresh")]
    entries = []
    with open(DECOMMISSION_LOG, encoding="utf-8") as f:
        for line in f:
            e = json.loads(line.strip())
            if date.fromisoformat(e["removed_date"]) >= since:
                entries.append(e)
    if not entries:
        return [types.TextContent(type="text", text=f"No decommissions in last {days} days. ✅")]
    lines = [f"Decommissioned (last {days} days):\n"]
    for e in entries:
        tag = "confirmed" if e["confirmed"] else "unconfirmed beta removal"
        replaced = f" → Replaced by: {e['replaced_by']}" if e.get("replaced_by") else ""
        lines.append(f"  ❌ {e['method']} {e['resource']} ({e['api_version']}) — {tag}{replaced}")
    return [types.TextContent(type="text", text="\n".join(lines))]


async def _call(args: dict) -> list[types.TextContent]:
    api_type = args.get("api_type", "graph")
    path = args["path"]
    method = args.get("method", "GET").upper()
    api_version = args.get("api_version", DEFAULT_API_VERSION)

    if _is_read_only() and is_write_method(method):
        return [
            types.TextContent(
                type="text",
                text=(
                    f"❌ Blocked: {method} {path} — GraphMind is in read-only mode "
                    "(GRAPHMIND_READ_ONLY=true). Only GET requests are allowed."
                ),
            )
        ]

    query_params = args.get("query_params", {})
    body = args.get("body")
    confirmed = args.get("confirmed", False)

    if (
        is_write_method(method)
        and is_write_confirmation_required()
        and not confirmed
    ):
        return [
            types.TextContent(
                type="text",
                text=build_confirmation_request(
                    method=method,
                    path=path,
                    api_version=api_version,
                    api_type=api_type,
                    query_params=query_params or None,
                    body=body,
                ),
            )
        ]

    paginate = args.get("paginate", False)
    max_pages = int(args.get("max_pages", DEFAULT_MAX_PAGES))
    aggregate = args.get("aggregate", True)
    sample_size = int(args.get("sample_size", DEFAULT_SAMPLE_SIZE))

    if api_type == "azure":
        result = call_azure(path, method, api_version, query_params, body)
    elif paginate and method == "GET":
        result = paginate_graph(
            path,
            method,
            api_version,
            query_params,
            body,
            max_pages=max_pages,
            aggregate=aggregate,
            sample_size=sample_size,
        )
    else:
        result = call_graph(path, method, api_version, query_params, body)

    if result["ok"]:
        data_json = json.dumps(result["data"], indent=2)
        pagination = result.get("pagination")
        header = f"✅ {method} /{api_version}{path}\n"
        if pagination and pagination.get("mode") not in ("single", "count"):
            header += (
                f"Paginated: {pagination.get('total_items', '?')} items, "
                f"{pagination.get('pages_fetched', '?')} page(s)"
            )
            if pagination.get("has_more"):
                header += " (more pages exist — increase max_pages or use $filter)"
            header += "\n\n"
        elif pagination and pagination.get("mode") == "count":
            header += f"Count: {result['data'].get('count', '?')}\n\n"
        if len(data_json) > MAX_RESPONSE_CHARS:
            data_json = data_json[:MAX_RESPONSE_CHARS] + "\n... (truncated)"
        return [types.TextContent(type="text", text=header + data_json)]
    err = result.get("error") or {}
    err_code = err.get("code", "?")
    err_msg = err.get("message", "No message")
    lines = [
        f"❌ {method} /{api_version}{path} → HTTP {result['status_code']}",
        f"Error: {err_code}: {err_msg}",
    ]
    if result["status_code"] == 404:
        index = get_index()
        pool = index.beta if api_version == "beta" else index.v1
        alternates = suggest_alternate_endpoints(path, method, api_version, candidates=pool)
        if alternates:
            lines.append("\nTry these related endpoints from the local index:")
            for ep in alternates:
                lines.append(f"  • {ep.method} {ep.path} — {ep.summary}")
            lines.append(
                "\nTip: For Cloud PC restore points use beta "
                "`GET .../cloudPCs/{cloudPC-id}/retrieveSnapshots()` (not `/snapshots`)."
            )
        else:
            lines.append(
                "\nCheck: path, permissions, api_version. "
                "If 404 on beta, try api_version='v1.0' or search_graph_api for alternates."
            )
    else:
        lines.append(
            "Check: path, permissions, request body. If 404 on beta, try api_version='v1.0'."
        )
    return [types.TextContent(type="text", text="\n".join(lines))]


async def main():
    # Start background index load so first tool call is faster
    asyncio.create_task(_ensure_index())
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
