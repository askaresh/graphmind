from __future__ import annotations
import httpx
from ..auth.token import get_token, GRAPH_SCOPES, AZURE_SCOPES

def _h(scopes): return {"Authorization": f"Bearer {get_token(scopes)}",
                        "Content-Type": "application/json"}

def call_graph(path, method="GET", api_version="v1.0", params=None, body=None):
    with httpx.Client(timeout=30) as c:
        r = c.request(method.upper(),
                      f"https://graph.microsoft.com/{api_version}{path}",
                      headers=_h(GRAPH_SCOPES), params=params or {}, json=body)
    return _norm(r)

def call_azure(path, method="GET", api_version="2024-01-01", params=None, body=None):
    p = {**(params or {}), "api-version": api_version}
    with httpx.Client(timeout=30) as c:
        r = c.request(method.upper(), f"https://management.azure.com{path}",
                      headers=_h(AZURE_SCOPES), params=p, json=body)
    return _norm(r)

def _norm(r: httpx.Response):
    try: data = r.json()
    except: data = {"raw": r.text}
    return {"status_code": r.status_code, "ok": r.is_success,
            "data": data, "error": data.get("error") if not r.is_success else None}
