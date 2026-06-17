import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from graphmind.spec.bootstrap import ensure_spec_repo, spec_files_present


def test_spec_files_present_with_fixture():
    fixture = Path(__file__).parent / "fixtures" / "spec"
    assert spec_files_present(fixture) is True


def test_spec_files_present_missing(tmp_path):
    assert spec_files_present(tmp_path) is False


@patch("graphmind.spec.bootstrap.subprocess.run")
def test_ensure_spec_repo_skips_clone_when_present(mock_run, tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "spec"
    result = ensure_spec_repo(str(fixture))
    assert result == fixture.resolve()
    mock_run.assert_not_called()


@patch("graphmind.spec.bootstrap.subprocess.run")
def test_ensure_spec_repo_clones_when_missing(mock_run, tmp_path, monkeypatch):
    target = tmp_path / "msgraph-metadata"

    def fake_clone(args, **kwargs):
        target.mkdir(parents=True)
        for rel in ("openapi/v1.0/openapi.yaml", "openapi/beta/openapi.yaml"):
            f = target / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text("paths: {}\n", encoding="utf-8")
        return subprocess.CompletedProcess(args, 0)

    mock_run.side_effect = fake_clone
    monkeypatch.setenv("SPEC_AUTO_CLONE", "true")

    result = ensure_spec_repo(str(target))
    assert result == target.resolve()
    mock_run.assert_called_once()
    assert mock_run.call_args.args[0][:2] == ["git", "clone"]


@patch("graphmind.spec.bootstrap.subprocess.run")
def test_ensure_spec_repo_raises_when_auto_clone_disabled(mock_run, tmp_path, monkeypatch):
    monkeypatch.setenv("SPEC_AUTO_CLONE", "false")
    with pytest.raises(FileNotFoundError, match="SPEC_AUTO_CLONE"):
        ensure_spec_repo(str(tmp_path / "missing"))
    mock_run.assert_not_called()
