from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from .loader import Endpoint, get_index

STRUCTURAL_FILTER_CEILING = int(os.getenv("STRUCTURAL_FILTER_CEILING", "500"))


def _matches_any_keyword(ep: Endpoint, keywords: list[str]) -> bool:
    haystack = " ".join(
        [
            ep.path.lower(),
            ep.summary.lower(),
            ep.description.lower(),
            ep.operation_id.lower(),
            " ".join(ep.tags).lower(),
        ]
    )
    return any(kw.lower() in haystack for kw in keywords)


@dataclass
class FilterIntent:
    api_version: str = "v1.0"
    method: Optional[str] = None
    tags: Optional[list[str]] = None
    keyword: Optional[str] = None
    keywords: Optional[list[str]] = None
    exclude_deprecated: bool = True
    granted_permissions: Optional[list[str]] = None


@dataclass
class FilterResult:
    endpoints: list[Endpoint]
    truncated: bool = False
    total_before_ceiling: int = 0


def structural_filter(intent: FilterIntent, ceiling: int | None = None) -> list[Endpoint]:
    return apply_structural_filter(intent, ceiling=ceiling).endpoints


def apply_structural_filter(intent: FilterIntent, ceiling: int | None = None) -> FilterResult:
    index = get_index()
    if intent.api_version == "both":
        candidates = index.v1 + index.beta
    elif intent.api_version == "beta":
        candidates = list(index.beta)
    else:
        candidates = list(index.v1)

    if intent.exclude_deprecated:
        candidates = [e for e in candidates if not e.deprecated]
    if intent.method:
        candidates = [e for e in candidates if e.method == intent.method.upper()]
    if intent.tags:
        norm = [t.lower() for t in intent.tags]
        candidates = [e for e in candidates if any(t.lower() in norm for t in e.tags)]
    if intent.granted_permissions:
        granted = set(intent.granted_permissions)
        candidates = [
            e
            for e in candidates
            if not e.permissions or any(p in granted for p in e.permissions)
        ]
    if intent.keyword:
        kw = intent.keyword.lower()
        candidates = [
            e
            for e in candidates
            if kw in e.path.lower()
            or kw in e.summary.lower()
            or kw in e.description.lower()
            or kw in e.operation_id.lower()
        ]
    if intent.keywords:
        candidates = [e for e in candidates if _matches_any_keyword(e, intent.keywords)]

    limit = ceiling if ceiling is not None else STRUCTURAL_FILTER_CEILING
    total = len(candidates)
    truncated = total > limit
    if truncated:
        candidates = candidates[:limit]

    return FilterResult(endpoints=candidates, truncated=truncated, total_before_ceiling=total)
