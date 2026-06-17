import asyncio
import os

import click
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table

load_dotenv()
console = Console()


@click.group()
def cli():
    """GraphMind — API-aware MCP server for Microsoft Graph."""
    pass


@cli.command()
def serve():
    """Start the MCP server."""
    import sys

    print("Starting GraphMind MCP server...", file=sys.stderr, flush=True)
    from graphmind.mcp.server import main

    asyncio.run(main())


@cli.command()
def bootstrap():
    """Clone msgraph-metadata if not present."""
    from graphmind.spec.bootstrap import ensure_spec_repo

    path = ensure_spec_repo(os.getenv("SPEC_REPO_PATH", "./msgraph-metadata"))
    console.print(f"[green]Spec repo ready at {path}[/green]")


@cli.command()
def refresh():
    """Pull latest spec + run diff pipeline."""
    from graphmind.spec.refresher import refresh as run_refresh

    run_refresh(os.getenv("SPEC_REPO_PATH", "./msgraph-metadata"))


@cli.command()
def scheduler():
    """Run the spec refresh scheduler (daily/weekly)."""
    from graphmind.scheduler import main as run_scheduler

    run_scheduler()


@cli.command()
def stats():
    """Show index statistics."""
    from graphmind.spec.loader import get_index, load_index

    idx = get_index()
    repo_path = os.getenv("SPEC_REPO_PATH", "./msgraph-metadata")
    try:
        load_index(repo_path)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    t = Table(title="GraphMind Index Stats")
    t.add_column("Version", style="cyan")
    t.add_column("Endpoints", justify="right", style="green")
    t.add_column("Deprecated", justify="right", style="yellow")
    t.add_row("v1.0", str(len(idx.v1)), str(sum(1 for e in idx.v1 if e.deprecated)))
    t.add_row("beta", str(len(idx.beta)), str(sum(1 for e in idx.beta if e.deprecated)))
    t.add_row("[bold]Total[/bold]", str(idx.total), "")
    console.print(t)


@cli.command()
@click.argument("query")
@click.option("--version", default="v1.0", help="API version: v1.0, beta, or both")
@click.option("--method", default=None)
@click.option("--top", default=5)
def search(query, version, method, top):
    """Quick terminal search (debug)."""
    from graphmind.spec.filter import FilterIntent, structural_filter
    from graphmind.spec.loader import get_index, load_index
    from graphmind.reranker.cross_encoder import rerank

    repo_path = os.getenv("SPEC_REPO_PATH", "./msgraph-metadata")
    try:
        load_index(repo_path)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc
    candidates = structural_filter(FilterIntent(api_version=version, method=method))
    results = rerank(query, candidates, top_k=top)
    console.print(f"\n[bold]Top {len(results)} for:[/bold] {query}\n")
    for ep in results:
        label = "v1.0" if ep.api_version == "v1.0" else "beta"
        console.print(f"  [{label}]  [cyan]{ep.method}[/cyan] {ep.path}")
        console.print(f"     [dim]{ep.summary}[/dim]\n")
