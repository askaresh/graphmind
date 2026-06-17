from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml
from rich.console import Console

console = Console()
SPEC_PATHS = {"v1.0": "openapi/v1.0/openapi.yaml", "beta": "openapi/beta/openapi.yaml"}
HTTP_METHODS = {"get", "post", "patch", "put", "delete"}


@dataclass
class Endpoint:
    path: str
    method: str
    api_version: str
    operation_id: str
    summary: str
    description: str
    tags: list[str]
    parameters: list[dict]
    request_body: Optional[dict]
    permissions: list[str]
    deprecated: bool
    chunk_id: str = field(default="", init=False)

    def __post_init__(self):
        self.chunk_id = hashlib.sha256(
            f"{self.api_version}::{self.path}::{self.method}".encode()
        ).hexdigest()[:16]

    def to_compact(self) -> str:
        return f"{self.method} {self.path}: {self.summary}"

    def to_rerank_text(self) -> str:
        parts = [f"{self.method} {self.path}", self.summary]
        if self.description:
            parts.append(self.description[:200])
        if self.tags:
            parts.append(f"tags: {', '.join(self.tags)}")
        if "()" in self.path:
            parts.append("OData bound function")
        return " — ".join(parts)

    def to_full_schema(self) -> str:
        lines = [
            f"## {self.method} {self.path}",
            f"**API Version:** {self.api_version}",
            f"**Summary:** {self.summary}",
        ]
        if self.description:
            lines.append(f"**Description:** {self.description[:400]}")
        if self.tags:
            lines.append(f"**Tags:** {', '.join(self.tags)}")
        if self.permissions:
            lines.append(f"**Required permissions:** {', '.join(self.permissions[:6])}")
        if self.deprecated:
            lines.append("\u26a0\ufe0f **DEPRECATED**")
        if self.parameters:
            lines.append("**Parameters:**")
            for p in self.parameters[:6]:
                req = "required" if p.get("required") else "optional"
                lines.append(
                    f"  - `{p.get('name')}` ({p.get('in', '?')}, {req}): "
                    f"{str(p.get('description', ''))[:80]}"
                )
        return "\n".join(lines)


class SpecIndex:
    def __init__(self):
        self.v1: list[Endpoint] = []
        self.beta: list[Endpoint] = []
        self._by_id: dict[str, Endpoint] = {}

    def load(self, repo_path: str, *, quiet: bool = False) -> bool:
        """Load OpenAPI specs. Returns True if at least one version was loaded."""
        out = console.stderr if quiet else console
        repo = Path(repo_path)
        loaded_any = False
        for version, rel in SPEC_PATHS.items():
            f = repo / rel
            if not f.exists():
                if not quiet:
                    out.print(f"[yellow]Spec not found: {f}[/yellow]")
                continue
            eps = self._parse(f, version)
            if version == "v1.0":
                self.v1 = eps
            else:
                self.beta = eps
            for ep in eps:
                self._by_id[ep.chunk_id] = ep
            if not quiet:
                out.print(f"[green]OK {version}: {len(eps):,} endpoints[/green]")
            loaded_any = True
        return loaded_any

    def _parse(self, spec_file: Path, version: str) -> list[Endpoint]:
        with open(spec_file, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        eps = []
        for path, item in spec.get("paths", {}).items():
            for method, op in item.items():
                if method not in HTTP_METHODS or not isinstance(op, dict):
                    continue
                perms = []
                for req in op.get("security", []):
                    for sl in req.values():
                        perms.extend(sl)
                ext = op.get("x-ms-permissions", [])
                if isinstance(ext, list):
                    perms.extend(ext)
                eps.append(
                    Endpoint(
                        path=path,
                        method=method.upper(),
                        api_version=version,
                        operation_id=op.get("operationId", ""),
                        summary=(op.get("summary") or "")[:200],
                        description=(op.get("description") or "")[:500],
                        tags=op.get("tags", []),
                        parameters=op.get("parameters", []),
                        request_body=op.get("requestBody"),
                        permissions=list(set(perms)),
                        deprecated=op.get("deprecated", False),
                    )
                )
        return eps

    def all_endpoints(self, api_version="v1.0") -> list[Endpoint]:
        return self.v1 if api_version == "v1.0" else self.beta

    def get_by_id(self, chunk_id: str) -> Optional[Endpoint]:
        return self._by_id.get(chunk_id)

    @property
    def total(self):
        return len(self.v1) + len(self.beta)


_index = SpecIndex()


def get_index() -> SpecIndex:
    return _index


def load_index(
    repo_path: str,
    *,
    required: bool = False,
    bootstrap: bool | None = None,
    quiet: bool = False,
) -> bool:
    """Load the spec index, optionally cloning the spec repo on first run."""
    if bootstrap is None:
        bootstrap = os.getenv("SPEC_AUTO_CLONE", "true").lower() in ("1", "true", "yes")
    if bootstrap:
        from .bootstrap import ensure_spec_repo

        try:
            ensure_spec_repo(repo_path)
        except FileNotFoundError:
            if required:
                raise
            return False

    loaded = get_index().load(repo_path, quiet=quiet)
    if required and not loaded:
        raise FileNotFoundError(
            f"No OpenAPI specs found under {repo_path}. "
            "Run: graphmind bootstrap  — or set SPEC_REPO_PATH."
        )
    return loaded
