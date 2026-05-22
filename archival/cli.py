from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from archival.db import get_connection, get_runs
from archival.jobs import JOBS
from archival.runner import run_job

app = typer.Typer(help="Archival - Manage and run archival jobs")
console = Console()

ROOT_DIR = Path(__file__).parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
DB_PATH = ROOT_DIR / "archival.db"


@app.command()
def run(
    job_name: str,
    chat: str = typer.Option(None, "--chat", "-c", help="Chat name or @username (telegram)"),
    chat_id: int = typer.Option(None, "--chat-id", help="Chat ID (telegram)"),
    limit: int = typer.Option(None, "--limit", "-l", help="Max messages to fetch (telegram)"),
    list_chats: bool = typer.Option(False, "--list-chats", help="List available chats (telegram)"),
):
    """Run an archival job."""
    if job_name not in JOBS:
        console.print(f"[red]Unknown job: {job_name}[/red]")
        console.print(f"Available jobs: {', '.join(JOBS.keys())}")
        raise typer.Exit(1)

    job_class = JOBS[job_name]
    job = job_class(data_dir=DATA_DIR, config_dir=CONFIG_DIR)

    console.print(f"[blue]Running job: {job_name}[/blue]")

    conn = get_connection(DB_PATH)

    if job_name == "telegram":
        result = job.run(chat=chat, chat_id=chat_id, limit=limit, list_chats=list_chats)
        from archival.db import save_run
        save_run(conn, job_name, result)
    else:
        result = run_job(job, conn)

    conn.close()

    if result.status.value == "success":
        console.print(f"[green]✓ {result.message}[/green]")
    else:
        console.print(f"[red]✗ {result.message}[/red]")
        raise typer.Exit(1)


@app.command("list")
def list_jobs():
    """List available archival jobs."""
    table = Table(title="Available Jobs")
    table.add_column("Name", style="cyan")
    table.add_column("Description")

    for name, job_class in JOBS.items():
        table.add_row(name, job_class.description)

    console.print(table)


@app.command()
def history(job_name: str | None = None, limit: int = 20):
    """Show run history for jobs."""
    conn = get_connection(DB_PATH)
    runs = get_runs(conn, job_name, limit)
    conn.close()

    if not runs:
        console.print("[dim]No runs found.[/dim]")
        return

    table = Table(title="Run History")
    table.add_column("ID", style="dim")
    table.add_column("Job", style="cyan")
    table.add_column("Status")
    table.add_column("Message")
    table.add_column("Started At")

    for run in runs:
        status_style = "green" if run["status"] == "success" else "red"
        table.add_row(
            str(run["id"]),
            run["job_name"],
            f"[{status_style}]{run['status']}[/{status_style}]",
            run["message"][:50] + "..." if len(run["message"] or "") > 50 else run["message"],
            run["started_at"],
        )

    console.print(table)


def main():
    app()


if __name__ == "__main__":
    main()
