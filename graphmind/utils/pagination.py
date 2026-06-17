from __future__ import annotations

import os
from typing import Any, Optional

import httpx

from ..auth.token import AZURE_SCOPES, GRAPH_SCOPES, get_token

DEFAULT_MAX_PAGES = int(os.getenv("GRAPHMIND_MAX_PAGES", "50"))
DEFAULT_SAMPLE_SIZE = int(os.getenv("GRAPHMIND_AGGREGATE_SAMPLE_SIZE", "10"))
REQUEST_TIMEOUT = int(os.getenv("GRAPHMIND_REQUEST_TIMEOUT", "60"))


def _headers(scopes, *, count: bool = False) -> dict:
    h = {"Authorization": f"Bearer {get_token(scopes)}"}
    if count:
        h["ConsistencyLevel"] = "eventual"
        h["Accept"] = "text/plain"
    else:
        h["Accept"] = "application/json"
        h["Content-Type"] = "application/json"
    return h


def _graph_url(path: str, api_version: str) -> str:
    return f"https://graph.microsoft.com/{api_version}{path}"


def _azure_url(path: str) -> str:
    return f"https://management.azure.com{path}"


def _norm(response: httpx.Response) -> dict:
    try:
        data = response.json()
    except Exception:
        data = {"raw": response.text}
    return {
        "status_code": response.status_code,
        "ok": response.is_success,
        "data": data,
        "error": data.get("error") if isinstance(data, dict) and not response.is_success else None,
    }


def call_graph(path, method="GET", api_version="v1.0", params=None, body=None):
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.request(
            method.upper(),
            _graph_url(path, api_version),
            headers=_headers(GRAPH_SCOPES),
            params=params or {},
            json=body,
        )
    return _norm(response)


def call_azure(path, method="GET", api_version="2024-01-01", params=None, body=None):
    params = {**(params or {}), "api-version": api_version}
    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        response = client.request(
            method.upper(),
            _azure_url(path),
            headers=_headers(AZURE_SCOPES),
            params=params,
            json=body,
        )
    return _norm(response)


def _is_count_path(path: str) -> bool:
    return path.rstrip("/").endswith("/$count")


def _extract_items(page_data: dict) -> list[Any]:
    if isinstance(page_data.get("value"), list):
        return page_data["value"]
    return []


def paginate_graph(
    path: str,
    method: str = "GET",
    api_version: str = "v1.0",
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    *,
    max_pages: int = DEFAULT_MAX_PAGES,
    aggregate: bool = False,
    sample_size: int = DEFAULT_SAMPLE_SIZE,
) -> dict:
    """
    Execute a Graph GET (or initial request) and optionally follow @odata.nextLink.

    Returns a normalized dict with keys: ok, status_code, data, error, pagination meta.
    """
    if method.upper() != "GET":
        result = call_graph(path, method, api_version, params, body)
        result["pagination"] = {"mode": "single", "pages_fetched": 1}
        return result

    params = dict(params or {})
    is_count = _is_count_path(path)

    with httpx.Client(timeout=REQUEST_TIMEOUT) as client:
        first = client.request(
            method.upper(),
            _graph_url(path, api_version),
            headers=_headers(GRAPH_SCOPES, count=is_count),
            params=params,
            json=body,
        )
        if not first.is_success:
            return _norm(first) | {"pagination": {"mode": "single", "pages_fetched": 1}}

        if is_count:
            return {
                "status_code": first.status_code,
                "ok": True,
                "data": {"count": first.text.strip(), "@odata.context": "count"},
                "error": None,
                "pagination": {"mode": "count", "pages_fetched": 1, "total_items": int(first.text.strip() or 0)},
            }

        try:
            page_data = first.json()
        except Exception:
            return _norm(first) | {"pagination": {"mode": "single", "pages_fetched": 1}}

        if not isinstance(page_data, dict) or "value" not in page_data:
            return {
                "status_code": first.status_code,
                "ok": True,
                "data": page_data,
                "error": None,
                "pagination": {"mode": "single", "pages_fetched": 1},
            }

        items = _extract_items(page_data)
        pages_fetched = 1
        next_url = page_data.get("@odata.nextLink")
        truncated = False

        while next_url and pages_fetched < max_pages:
            response = client.get(next_url, headers=_headers(GRAPH_SCOPES))
            if not response.is_success:
                truncated = True
                break
            page_data = response.json()
            items.extend(_extract_items(page_data))
            pages_fetched += 1
            next_url = page_data.get("@odata.nextLink")

        has_more = bool(next_url)
        if has_more:
            truncated = True

        odata_count = page_data.get("@odata.count") if isinstance(page_data, dict) else None
        total_items = odata_count if odata_count is not None else len(items)

        pagination = {
            "mode": "aggregate" if aggregate else "merged",
            "pages_fetched": pages_fetched,
            "total_items": total_items,
            "has_more": has_more,
            "truncated_by_max_pages": truncated,
            "max_pages": max_pages,
        }

        if aggregate:
            data = {
                "summary": pagination,
                "sample": items[:sample_size],
                "sample_size": min(sample_size, len(items)),
            }
        else:
            data = {
                "@odata.context": first.json().get("@odata.context") if first.content else None,
                "value": items,
                **({"@odata.nextLink": next_url} if has_more else {}),
                "pagination": pagination,
            }

        return {
            "status_code": first.status_code,
            "ok": True,
            "data": data,
            "error": None,
            "pagination": pagination,
        }
