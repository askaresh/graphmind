"""Query expansion and domain hints for Graph API search."""
from __future__ import annotations

from dataclasses import dataclass, field

from .loader import Endpoint

# Natural-language terms → API vocabulary for reranking
QUERY_SYNONYMS: dict[str, str] = {
    "restore point": "snapshot retrieveSnapshots cloudPcSnapshot",
    "restore points": "snapshot retrieveSnapshots cloudPcSnapshot",
    "point in time": "snapshot retrieveSnapshots",
    "backup": "snapshot retrieveSnapshots",
}

# When the query mentions these domains, prefer beta + narrow tags/keywords
DOMAIN_HINTS: tuple[dict, ...] = (
    {
        "patterns": ("cloud pc", "cloudpc", "windows 365", "virtual endpoint", "w365"),
        "prefer_beta": True,
        "tags": ("deviceManagement.virtualEndpoint",),
        "keywords": ("cloudPC", "virtualEndpoint"),
    },
    {
        "patterns": ("restore point", "restore points", "snapshot"),
        "prefer_beta": True,
        "tags": ("deviceManagement.virtualEndpoint",),
        "keywords": ("snapshot", "retrieveSnapshots"),
    },
)

# Failed path → known-good alternatives (method → list of path templates)
KNOWN_ALTERNATES: dict[str, dict[str, list[str]]] = {
    "beta": {
        "GET": {
            "/deviceManagement/virtualEndpoint/snapshots": [
                "/deviceManagement/virtualEndpoint/cloudPCs/{cloudPC-id}/retrieveSnapshots()",
            ],
            "/deviceManagement/virtualEndpoint/snapshots/$count": [
                "/deviceManagement/virtualEndpoint/cloudPCs/{cloudPC-id}/retrieveSnapshots()",
            ],
        },
    },
}


@dataclass
class SearchHints:
    prefer_beta: bool = False
    tags: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    expanded_query: str = ""


def _normalize_path(path: str) -> str:
    base = path.split("?", 1)[0].rstrip("/")
    if not base.startswith("/"):
        base = f"/{base}"
    return base


def expand_query(query: str) -> str:
    """Append API synonym terms when natural-language phrases appear in the query."""
    lowered = query.lower()
    extras: list[str] = []
    for phrase, addition in QUERY_SYNONYMS.items():
        if phrase in lowered:
            extras.append(addition)
    if not extras:
        return query
    return f"{query} {' '.join(extras)}"


def infer_search_hints(
    query: str,
    *,
    api_version: str,
    tags: list[str] | None = None,
    keyword: str | None = None,
) -> SearchHints:
    """Derive beta preference, tags, and keywords from a natural-language query."""
    lowered = query.lower()
    prefer_beta = False
    hint_tags: list[str] = []
    hint_keywords: list[str] = []

    for hint in DOMAIN_HINTS:
        if any(p in lowered for p in hint["patterns"]):
            if hint.get("prefer_beta"):
                prefer_beta = True
            hint_tags.extend(hint.get("tags", ()))
            hint_keywords.extend(hint.get("keywords", ()))

    # Only auto-hint when caller did not already narrow the search
    applied_tags = list(tags) if tags else list(dict.fromkeys(hint_tags))
    applied_keywords: list[str] = []
    if keyword:
        applied_keywords = [keyword]
    elif hint_keywords:
        applied_keywords = list(dict.fromkeys(hint_keywords))

    expanded = expand_query(query)
    return SearchHints(
        prefer_beta=prefer_beta and api_version == "v1.0",
        tags=applied_tags,
        keywords=applied_keywords,
        expanded_query=expanded,
    )


def suggest_alternate_endpoints(
    path: str,
    method: str,
    api_version: str,
    *,
    candidates: list[Endpoint],
    limit: int = 5,
) -> list[Endpoint]:
    """Suggest index entries when a live call returns 404."""
    method = method.upper()
    norm_path = _normalize_path(path)
    seen: set[str] = set()
    results: list[Endpoint] = []

    def add(ep: Endpoint) -> None:
        key = f"{ep.api_version}::{ep.path}::{ep.method}"
        if key not in seen and ep.path != norm_path:
            seen.add(key)
            results.append(ep)

    known = KNOWN_ALTERNATES.get(api_version, {}).get(method, {})
    for alt_path in known.get(norm_path, []):
        for ep in candidates:
            if ep.method == method and ep.path == alt_path:
                add(ep)

    if len(results) >= limit:
        return results[:limit]

    parts = norm_path.strip("/").split("/")
    parent = f"/{'/'.join(parts[:-1])}" if len(parts) > 1 else ""
    segment = parts[-1].lower() if parts else ""

    for ep in candidates:
        if ep.method != method:
            continue
        if parent and parent in ep.path and ep.path != norm_path:
            add(ep)
        elif segment and segment in ep.path.lower() and ep.path != norm_path:
            add(ep)
        elif segment in ("snapshots",) and "retrieveSnapshots" in ep.path:
            add(ep)

    return results[:limit]
