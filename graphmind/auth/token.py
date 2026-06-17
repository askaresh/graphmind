from __future__ import annotations

import base64
import json
import os
from pathlib import Path

import msal

GRAPH_SCOPES = ["https://graph.microsoft.com/.default"]
AZURE_SCOPES = ["https://management.azure.com/.default"]
CACHE_PATH = Path(os.getenv("TOKEN_CACHE_PATH", "./.graphmind_token_cache.json"))

_app = None
_cache = msal.SerializableTokenCache()


def _load_cache():
    if CACHE_PATH.exists():
        _cache.deserialize(CACHE_PATH.read_text(encoding="utf-8"))


def _save_cache():
    if _cache.has_state_changed:
        CACHE_PATH.write_text(_cache.serialize(), encoding="utf-8")


def _build_app():
    tid, cid = os.environ["TENANT_ID"], os.environ["CLIENT_ID"]
    mode = os.getenv("AUTH_MODE", "interactive")
    auth = f"https://login.microsoftonline.com/{tid}"
    if mode == "interactive":
        return msal.PublicClientApplication(cid, authority=auth, token_cache=_cache)
    cred = (
        os.environ["CLIENT_SECRET"]
        if mode == "client_secret"
        else {"private_key": Path(os.environ["CERT_PATH"]).read_text(encoding="utf-8")}
    )
    return msal.ConfidentialClientApplication(
        cid, authority=auth, client_credential=cred, token_cache=_cache
    )


def get_token(scopes=GRAPH_SCOPES) -> str:
    global _app
    if _app is None:
        _load_cache()
        _app = _build_app()
    accounts = _app.get_accounts()
    result = _app.acquire_token_silent(scopes, account=accounts[0]) if accounts else None
    if not result:
        mode = os.getenv("AUTH_MODE", "interactive")
        result = (
            _app.acquire_token_interactive(scopes=scopes)
            if mode == "interactive"
            else _app.acquire_token_for_client(scopes=scopes)
        )
    _save_cache()
    if "access_token" not in result:
        raise RuntimeError(f"Auth failed: {result.get('error_description', '?')}")
    return result["access_token"]


def get_granted_permissions() -> list[str]:
    payload_b64 = get_token().split(".")[1] + "=="
    payload = json.loads(base64.urlsafe_b64decode(payload_b64))
    return list(set(payload.get("scp", "").split() + payload.get("roles", [])))
