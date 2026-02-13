# maios/cli/main.py
import typer
from rich.console import Console

app = typer.Typer(
    name="maios",
    help="Metamorphic AI Orchestration System",
)
console = Console()


def version_callback(value: bool):
    if value:
        console.print("MAIOS version 0.1.0")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
):
    """MAIOS - Metamorphic AI Orchestration System."""
    pass


@app.command()
def server():
    """Start the API server."""
    import uvicorn

    console.print("[bold cyan]Starting MAIOS API server...[/bold cyan]")
    uvicorn.run(
        "maios.api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )


@app.command()
def worker():
    """Start a Celery worker."""
    console.print("[bold cyan]Starting MAIOS worker...[/bold cyan]")
    from maios.workers.celery_app import app as celery_app

    celery_app.worker_main(["worker", "--loglevel=info"])


@app.command()
def version_cmd():
    """Show version information."""
    console.print("[bold]MAIOS[/bold] version [cyan]0.1.0[/cyan]")
