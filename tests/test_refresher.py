import hashlib
from datetime import date
from pathlib import Path

from graphmind.spec.refresher import run_diff_pipeline


def make_meta(path, method="GET", version="v1.0", content_hash="abc123"):
    chunk_id = hashlib.sha256(f"{version}::{path}::{method}".encode()).hexdigest()[:16]
    return chunk_id, {
        "chunk_id": chunk_id,
        "path": path,
        "method": method,
        "api_version": version,
        "content_hash": content_hash,
        "indexed_at": str(date.today()),
        "source_commit": "deadbeef",
    }


def test_diff_identifies_changes():
    cid1, meta1 = make_meta("/users")
    cid2, meta2 = make_meta("/groups")
    cid3, meta3 = make_meta("/devices", content_hash="old")
    old = {cid1: meta1, cid3: meta3}
    _, nm2 = make_meta("/groups")
    _, nm3 = make_meta("/devices", content_hash="new")
    new = {cid2: nm2, cid3: nm3}
    added = set(new) - set(old)
    removed = set(old) - set(new)
    changed = {c for c in set(old) & set(new) if old[c]["content_hash"] != new[c]["content_hash"]}
    assert cid2 in added
    assert cid1 in removed
    assert cid3 in changed


def test_run_diff_pipeline_with_fixture(tmp_path, monkeypatch):
    fixture = Path(__file__).parent / "fixtures" / "spec"
    monkeypatch.chdir(tmp_path)
    report = run_diff_pipeline(str(fixture), skip_git_pull=True)
    assert report["total_indexed"] == 6
    assert report["v1_count"] == 5
    assert report["beta_count"] == 1
    assert report["added"] == 6
