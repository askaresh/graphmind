"""
ci_refresh.py
Headless refresh runner for GitHub Actions.
Runs the full diff pipeline and writes graphmind_diff_report.json.
No git pull needed — actions/checkout already has the latest spec.
"""
import json
import os
from pathlib import Path

from rich.console import Console

from graphmind.spec.refresher import run_diff_pipeline

console = Console()
REPORT_PATH = Path("graphmind_diff_report.json")


def main():
    repo_path = os.getenv("SPEC_REPO_PATH", "./msgraph-metadata")
    console.print("[bold cyan]GraphMind CI Spec Refresh[/bold cyan]")
    report = run_diff_pipeline(repo_path, skip_git_pull=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    console.print(
        f"[green]Done — Added:{report['added']} Changed:{report['changed']} "
        f"Decommissioned:{len(report['decommissioned'])} Suspect:{len(report['suspect_beta'])}[/green]"
    )


if __name__ == "__main__":
    main()
