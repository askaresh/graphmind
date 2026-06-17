from unittest.mock import MagicMock, patch

import httpx

from graphmind.utils.pagination import paginate_graph


def _mock_response(status=200, json_data=None, text="", url="https://graph.microsoft.com/v1.0/users"):
    response = MagicMock(spec=httpx.Response)
    response.status_code = status
    response.is_success = 200 <= status < 300
    response.url = url
    response.text = text
    response.content = b"{}"
    response.json.return_value = json_data or {}
    return response


@patch("graphmind.utils.pagination.get_token", return_value="fake-token")
@patch("graphmind.utils.pagination.httpx.Client")
def test_paginate_aggregate(mock_client_cls, _token):
    page1 = _mock_response(json_data={
        "@odata.context": "users",
        "value": [{"id": "1"}, {"id": "2"}],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=abc",
    })
    page2 = _mock_response(json_data={
        "@odata.context": "users",
        "value": [{"id": "3"}],
    })
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.request.return_value = page1
    mock_client.get.return_value = page2
    mock_client_cls.return_value = mock_client

    result = paginate_graph("/users", params={"$top": "2"}, aggregate=True, sample_size=2)

    assert result["ok"] is True
    assert result["pagination"]["total_items"] == 3
    assert result["pagination"]["pages_fetched"] == 2
    assert len(result["data"]["sample"]) == 2
    assert result["data"]["summary"]["has_more"] is False


@patch("graphmind.utils.pagination.get_token", return_value="fake-token")
@patch("graphmind.utils.pagination.httpx.Client")
def test_paginate_respects_max_pages(mock_client_cls, _token):
    page = _mock_response(json_data={
        "value": [{"id": "1"}],
        "@odata.nextLink": "https://graph.microsoft.com/v1.0/users?$skiptoken=abc",
    })
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.request.return_value = page
    mock_client.get.return_value = page
    mock_client_cls.return_value = mock_client

    result = paginate_graph("/users", aggregate=True, max_pages=2)

    assert result["pagination"]["pages_fetched"] == 2
    assert result["pagination"]["has_more"] is True
    assert result["pagination"]["truncated_by_max_pages"] is True


@patch("graphmind.utils.pagination.get_token", return_value="fake-token")
@patch("graphmind.utils.pagination.httpx.Client")
def test_count_endpoint(mock_client_cls, _token):
    response = _mock_response(status=200, text="42")
    response.json.side_effect = ValueError("not json")
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.request.return_value = response
    mock_client_cls.return_value = mock_client

    result = paginate_graph("/users/$count")

    assert result["ok"] is True
    assert result["data"]["count"] == "42"
    assert result["pagination"]["total_items"] == 42
