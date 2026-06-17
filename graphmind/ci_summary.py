"""
ci_summary.py
Reads graphmind_diff_report.json and writes a Markdown table
to $GITHUB_STEP_SUMMARY — visible in the Actions run UI.
"""
import json
import os
import sys
from pathlib import Path

REPORT_PATH = Path("graphmind_diff_report.json")


def _safe_print(text: str):
    try:
        print(text)
    except UnicodeEncodeError:
        # Windows consoles may not support emoji in step summary markdown
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")


def main():
    if not REPORT_PATH.exists():
        print("No report found — skipping summary.")
        return

    r = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    lines = [
        "## GraphMind — Daily Spec Refresh",
        f"**Date:** {r['run_date']}  |  **Spec commit:** `{r['spec_commit'][:8]}`",
        "",
        "### Index",
        "| Version | Endpoints |",
        "|---------|-----------|",
        f"| v1.0    | {r['v1_count']:,} |",
        f"| beta    | {r['beta_count']:,} |",
        f"| **Total** | **{r['total_indexed']:,}** |",
        "",
        "### Changes",
        "| | Count |",
        "|---|---|",
        f"| Added              | {r['added']} |",
        f"| Changed            | {r['changed']} |",
        f"| Decommissioned     | {len(r['decommissioned'])} |",
        f"| Suspect beta       | {len(r['suspect_beta'])} |",
    ]

    if r["added_sample"]:
        lines += ["", "### Sample New Endpoints"]
        for p in r["added_sample"]:
            lines.append(f"- `{p}`")

    if r["decommissioned"]:
        lines += ["", "### Decommissioned Endpoints"]
        for d in r["decommissioned"]:
            tag = "confirmed" if d["confirmed"] else "unconfirmed (beta silent removal)"
            lines.append(f"- `{d['endpoint']}` ({d['version']}) — {tag}")

    if r["suspect_beta"]:
        lines += ["", "### Suspect Beta (grace period active — not yet removed)"]
        for ep in r["suspect_beta"]:
            lines.append(f"- `{ep}`")

    summary = "\n".join(lines)
    _safe_print(summary)

    gss = os.getenv("GITHUB_STEP_SUMMARY")
    if gss:
        with open(gss, "a", encoding="utf-8") as f:
            f.write(summary + "\n")


if __name__ == "__main__":
    main()
