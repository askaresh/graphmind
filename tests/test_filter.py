import pytest
from unittest.mock import patch

from graphmind.spec.filter import FilterIntent, apply_structural_filter, structural_filter
from graphmind.spec.loader import Endpoint, get_index, load_index


def make_ep(path="/users", method="GET", tags=None, permissions=None, deprecated=False, version="v1.0"):
    return Endpoint(
        path=path,
        method=method,
        api_version=version,
        operation_id="test",
        summary="Test endpoint",
        description="",
        tags=tags or ["users"],
        parameters=[],
        request_body=None,
        permissions=permissions or ["User.Read"],
        deprecated=deprecated,
    )


SAMPLE = [
    make_ep("/users", "GET", ["users"], ["User.Read"]),
    make_ep("/groups", "GET", ["groups"], ["Group.Read.All"]),
    make_ep("/groups", "POST", ["groups"], ["Group.ReadWrite.All"]),
    make_ep("/auth", "GET", ["authentication"], ["UserAuthenticationMethod.Read.All"]),
    make_ep("/old", "GET", ["users"], deprecated=True),
]


@patch("graphmind.spec.filter.get_index")
def test_method_filter(mock):
    mock.return_value.v1 = SAMPLE
    mock.return_value.beta = []
    results = structural_filter(FilterIntent(method="POST"))
    assert all(e.method == "POST" for e in results)


@patch("graphmind.spec.filter.get_index")
def test_deprecated_excluded(mock):
    mock.return_value.v1 = SAMPLE
    mock.return_value.beta = []
    results = structural_filter(FilterIntent(exclude_deprecated=True))
    assert not any(e.deprecated for e in results)


@patch("graphmind.spec.filter.get_index")
def test_permission_filter(mock):
    mock.return_value.v1 = SAMPLE
    mock.return_value.beta = []
    results = structural_filter(FilterIntent(granted_permissions=["User.Read"]))
    assert all("User.Read" in e.permissions for e in results)


@patch("graphmind.spec.filter.get_index")
def test_structural_filter_ceiling(mock):
    many = [make_ep(f"/resource{i}", "GET") for i in range(10)]
    mock.return_value.v1 = many
    mock.return_value.beta = []
    result = apply_structural_filter(FilterIntent(), ceiling=3)
    assert len(result.endpoints) == 3
    assert result.truncated is True
    assert result.total_before_ceiling == 10
