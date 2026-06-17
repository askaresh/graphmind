"""
spec/refresher.py
Daily/weekly diff pipeline with:
  - Added / changed / decommissioned endpoint tracking
  - Beta grace period (3 days before hard decommission)
  - PROMOTION DETECTION: beta endpoints that graduate to v1.0
    are logged to graphmind_promotion_log.json
"""
from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import date, datetime, timezone
from pathlib import Path

from rich.console import Console

from .bootstrap import ensure_spec_repo
from .loader import Endpoint, get_index

console = Console()
MANIFEST_PATH = Path("./graphmind_manifest.json")
DECOMMISSION_LOG = Path("./graphmind_decommission_log.jsonl")
PROMOTION_LOG = Path("./graphmind_promotion_log.json")
BETA_GRACE_DAYS = 3


def _content_hash(ep: Endpoint) -> str:
    return hashlib.sha256(
        f"{ep.summary}{ep.description}{ep.permissions}{ep.deprecated}".encode()
    ).hexdigest()[:12]


def _load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {"chunks": {}}


def _save_manifest(m: dict):
    MANIFEST_PATH.write_text(json.dumps(m, indent=2))


def _log_decommission(meta: dict, confirmed: bool):
    entry = {
        "chunk_id": meta["chunk_id"],
        "resource": meta["path"],
        "method": meta["method"],
        "api_version": meta["api_version"],
        "removed_date": str(date.today()),
        "confirmed": confirmed,
        "replaced_by": meta.get("replaced_by"),
    }
    with open(DECOMMISSION_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _detect_promotions(index) -> dict:
    """Detect beta endpoints that also exist in v1.0. Returns {beta_chunk_id: v1.0_path}."""
    promotions = json.loads(PROMOTION_LOG.read_text()) if PROMOTION_LOG.exists() else {}
    v1_paths = {(ep.path, ep.method) for ep in index.v1}
    new_promotions = 0

    for ep in index.beta:
        if (ep.path, ep.method) in v1_paths and ep.chunk_id not in promotions:
            promotions[ep.chunk_id] = ep.path
            new_promotions += 1
            console.print(f"[blue]  PROMOTED beta->v1.0: {ep.method} {ep.path}[/blue]")

    if new_promotions:
        PROMOTION_LOG.write_text(json.dumps(promotions, indent=2))
        console.print(f"[blue]  {new_promotions} new beta->v1.0 promotions logged[/blue]")

    return promotions


def git_pull(repo_path: str) -> str:
    subprocess.run(["git", "pull", "--ff-only"], cwd=repo_path, capture_output=True, check=False)
    return subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def resolve_spec_commit(repo_path: str, *, skip_git_pull: bool) -> str:
    if not skip_git_pull:
        return git_pull(repo_path)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_path,
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        return result.stdout.strip()
    return "local"


def run_diff_pipeline(repo_path: str, *, skip_git_pull: bool = False) -> dict:
    """Run the full spec diff pipeline. Returns a report dict."""
    new_commit = resolve_spec_commit(repo_path, skip_git_pull=skip_git_pull)
    if not skip_git_pull:
        console.print(f"  HEAD -> {new_commit}")

    index = get_index()
    index.load(repo_path)

    new_snapshot = {
        ep.chunk_id: {
            "chunk_id": ep.chunk_id,
            "path": ep.path,
            "method": ep.method,
            "api_version": ep.api_version,
            "content_hash": _content_hash(ep),
            "source_commit": new_commit,
            "indexed_at": str(date.today()),
        }
        for ep in index.v1 + index.beta
    }

    old_chunks = _load_manifest().get("chunks", {})
    old_ids, new_ids = set(old_chunks), set(new_snapshot)
    added = new_ids - old_ids
    removed = old_ids - new_ids
    changed = {
        cid
        for cid in old_ids & new_ids
        if old_chunks[cid]["content_hash"] != new_snapshot[cid]["content_hash"]
    }

    decommissioned: list[dict] = []
    suspect_beta: list[str] = []

    for chunk_id in removed:
        meta = old_chunks[chunk_id]
        method, path = meta["method"], meta["path"]
        if meta.get("api_version") == "beta":
            first = meta.get("missing_since")
            if not first:
                new_snapshot[chunk_id] = {**meta, "missing_since": str(date.today())}
                suspect_beta.append(f"{method} {path}")
                console.print(f"[yellow]  SUSPECT (beta): {method} {path}[/yellow]")
                continue
            if (date.today() - date.fromisoformat(first)).days < BETA_GRACE_DAYS:
                new_snapshot[chunk_id] = {**meta}
                continue
            _log_decommission(meta, confirmed=False)
            decommissioned.append(
                {"endpoint": f"{method} {path}", "version": "beta", "confirmed": False}
            )
            console.print(f"[red]  DECOMMISSIONED (beta): {method} {path}[/red]")
        else:
            _log_decommission(meta, confirmed=True)
            decommissioned.append(
                {"endpoint": f"{method} {path}", "version": "v1.0", "confirmed": True}
            )
            console.print(f"[red]  DECOMMISSIONED (v1.0): {method} {path}[/red]")

    _detect_promotions(index)

    _save_manifest(
        {
            "chunks": new_snapshot,
            "last_refresh": datetime.now(timezone.utc).isoformat(),
            "last_commit": new_commit,
        }
    )

    return {
        "run_date": str(date.today()),
        "spec_commit": new_commit,
        "total_indexed": index.total,
        "v1_count": len(index.v1),
        "beta_count": len(index.beta),
        "added": len(added),
        "changed": len(changed),
        "removed": len(removed),
        "decommissioned": decommissioned,
        "suspect_beta": suspect_beta,
        "added_sample": [new_snapshot[cid]["path"] for cid in list(added)[:10]],
    }


def refresh(repo_path: str):
    console.print("[bold cyan]GraphMind Spec Refresh[/bold cyan]")
    ensure_spec_repo(repo_path)
    report = run_diff_pipeline(repo_path, skip_git_pull=False)
    console.print(
        f"\n[bold green]Refresh complete:[/bold green]\n"
        f"  Added: {report['added']:,} | Changed: {report['changed']:,} | "
        f"Removed: {report['removed']:,} | Total: {report['total_indexed']:,}"
    )
