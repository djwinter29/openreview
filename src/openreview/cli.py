from __future__ import annotations

import typer
from rich import print

from openreview import __version__

app = typer.Typer(help="openreview - AI-assisted PR review automation")


@app.callback()
def _root() -> None:
    pass


@app.command()
def version() -> None:
    print(f"openreview {__version__}")


@app.command()
def plan() -> None:
    print("[bold]MVP Plan[/bold]")
    print("1) Collect Azure DevOps PR threads + latest diff")
    print("2) Run AI reviewer policy on changed files")
    print("3) Upsert comments: create/update/resolve")
    print("4) Emit CI summary")


if __name__ == "__main__":
    app()
