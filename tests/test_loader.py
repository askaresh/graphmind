from pathlib import Path

import pytest

from graphmind.spec.loader import get_index, load_index

FIXTURE_SPEC = Path(__file__).parent / "fixtures" / "spec"


@pytest.fixture(autouse=True)
def reset_index():
    idx = get_index()
    idx.v1 = []
    idx.beta = []
    idx._by_id = {}
    yield
    idx.v1 = []
    idx.beta = []
    idx._by_id = {}


def test_load_fixture_spec():
    assert load_index(str(FIXTURE_SPEC)) is True
    idx = get_index()
    assert len(idx.v1) == 5
    assert len(idx.beta) == 1
    assert idx.total == 6


def test_load_missing_spec_returns_false(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_AUTO_CLONE", "false")
    assert load_index(str(tmp_path), bootstrap=True) is False


def test_load_required_raises_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_AUTO_CLONE", "false")
    with pytest.raises(FileNotFoundError):
        load_index(str(tmp_path), required=True, bootstrap=True)


def test_get_by_id_roundtrip():
    load_index(str(FIXTURE_SPEC))
    ep = get_index().v1[0]
    assert get_index().get_by_id(ep.chunk_id) == ep
