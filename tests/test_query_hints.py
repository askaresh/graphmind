from graphmind.spec.loader import Endpoint
from graphmind.spec.query_hints import (
    expand_query,
    infer_search_hints,
    suggest_alternate_endpoints,
)


def _ep(path: str, summary: str = "", version: str = "beta") -> Endpoint:
    return Endpoint(
        path=path,
        method="GET",
        api_version=version,
        operation_id="test.op",
        summary=summary,
        description="",
        tags=["deviceManagement.virtualEndpoint"],
        parameters=[],
        request_body=None,
        permissions=[],
        deprecated=False,
    )


def test_expand_query_restore_points():
    expanded = expand_query("how many restore points for cloud pc")
    assert "retrieveSnapshots" in expanded
    assert "snapshot" in expanded


def test_infer_search_hints_cloud_pc():
    hints = infer_search_hints("list cloud pc snapshots", api_version="v1.0")
    assert hints.prefer_beta is True
    assert "deviceManagement.virtualEndpoint" in hints.tags
    assert "retrieveSnapshots" in hints.keywords or "snapshot" in hints.keywords


def test_infer_search_hints_respects_explicit_keyword():
    hints = infer_search_hints("users", api_version="v1.0", keyword="mail")
    assert hints.keywords == ["mail"]


def test_suggest_alternate_endpoints_snapshots():
    retrieve = _ep(
        "/deviceManagement/virtualEndpoint/cloudPCs/{cloudPC-id}/retrieveSnapshots()",
        "Invoke function retrieveSnapshots",
    )
    collection = _ep(
        "/deviceManagement/virtualEndpoint/snapshots",
        "Get snapshots from deviceManagement",
    )
    alts = suggest_alternate_endpoints(
        "/deviceManagement/virtualEndpoint/snapshots",
        "GET",
        "beta",
        candidates=[collection, retrieve],
    )
    assert any("retrieveSnapshots" in ep.path for ep in alts)
