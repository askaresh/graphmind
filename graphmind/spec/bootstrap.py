from __future__ import annotations

import os
import subprocess
from pathlib import Path

from rich.console import Console

from .loader import SPEC_PATHS

console = Console()
DEFAULT_REPO_URL = "https://github.com/microsoftgraph/msgraph-metadata.git"


def spec_files_present(repo_path: Path) -> bool:
    return all((repo_path / rel).exists() for rel in SPEC_PATHS.values())


def _auto_clone_enabled() -> bool:
    return os.getenv("SPEC_AUTO_CLONE", "true").lower() in ("1", "true", "yes")


def ensure_spec_repo(repo_path: str) -> Path:
    """
    Ensure msgraph-metadata is present at repo_path.
    Clones on first run when SPEC_AUTO_CLONE=true (default).
    """
    path = Path(repo_path)
    if spec_files_present(path):
        return path.resolve()

    if not _auto_clone_enabled():
        raise FileNotFoundError(
            f"No OpenAPI specs under {path}. Set SPEC_AUTO_CLONE=true or clone manually:\n"
            f"  git clone {DEFAULT_REPO_URL} {path}"
        )

    url = os.getenv("SPEC_REPO_URL", DEFAULT_REPO_URL)

    if (path / ".git").is_dir():
        console.print("[cyan]Spec repo present but OpenAPI files missing — pulling latest...[/cyan]")
        subprocess.run(["git", "pull", "--ff-only"], cwd=path, check=True)
        if spec_files_present(path):
            return path.resolve()

    if path.exists() and any(path.iterdir()) and not (path / ".git").is_dir():
        raise FileNotFoundError(
            f"{path} exists but is not msgraph-metadata. Remove it or set SPEC_REPO_PATH elsewhere."
        )

    path.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Cloning {url} -> {path} (shallow)...[/cyan]")
    subprocess.run(["git", "clone", "--depth", "1", url, str(path)], check=True)

    if not spec_files_present(path):
        raise FileNotFoundError(f"Clone completed but OpenAPI files not found under {path}.")
    console.print("[green]Spec repo ready.[/green]")
    return path.resolve()
