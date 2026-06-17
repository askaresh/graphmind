from graphmind.utils.write_guard import (
    build_confirmation_request,
    is_write_confirmation_required,
    is_write_method,
)


def test_is_write_method():
    assert is_write_method("POST")
    assert is_write_method("patch")
    assert not is_write_method("GET")


def test_build_confirmation_request_includes_action():
    text = build_confirmation_request(
        method="POST",
        path="/deviceManagement/virtualEndpoint/cloudPCs/abc/reboot",
        api_version="v1.0",
    )
    assert "reboot" in text.lower()
    assert "confirmed: true" in text.lower()


def test_is_write_confirmation_required_default(monkeypatch):
    monkeypatch.delenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", raising=False)
    assert is_write_confirmation_required() is True


def test_is_write_confirmation_required_disabled(monkeypatch):
    monkeypatch.setenv("GRAPHMIND_REQUIRE_WRITE_CONFIRMATION", "false")
    assert is_write_confirmation_required() is False
