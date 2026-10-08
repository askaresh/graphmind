import subprocess
import sys


def test_cli_imports():
    from graphmind.cli import cli

    assert cli is not None


def test_cli_module_help():
    result = subprocess.run(
        [sys.executable, "-m", "graphmind.cli", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "stats" in result.stdout
