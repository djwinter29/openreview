from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from openreview import __version__
from openreview.azure_devops import AzureDevOpsClient
from openreview.review_sync import ReviewFinding, plan_sync

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


def _env_or_option(value: str | None, env_name: str) -> str:
    if value:
        return value
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    raise typer.BadParameter(f"Missing value. Provide --{env_name.lower().replace('_','-')} or set {env_name}")


@app.command()
def sync(
    pr_id: int = typer.Option(..., help="Azure DevOps PR ID"),
    findings_file: Path = typer.Option(..., exists=True, help="Path to findings JSON"),
    organization: str | None = typer.Option(None, help="Azure DevOps organization"),
    project: str | None = typer.Option(None, help="Azure DevOps project"),
    repository_id: str | None = typer.Option(None, help="Azure DevOps repository id"),
    pat: str | None = typer.Option(None, help="Azure DevOps PAT"),
    dry_run: bool = typer.Option(False, help="Only print planned actions"),
) -> None:
    organization = _env_or_option(organization, "AZDO_ORG")
    project = _env_or_option(project, "AZDO_PROJECT")
    repository_id = _env_or_option(repository_id, "AZDO_REPO_ID")
    pat = _env_or_option(pat, "AZDO_PAT")

    findings_raw = json.loads(findings_file.read_text())
    findings = [ReviewFinding(**item) for item in findings_raw]

    client = AzureDevOpsClient(
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
    )

    existing_threads = client.get_pull_request_threads(pr_id)
    actions = plan_sync(findings, existing_threads)

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {action.kind} [{action.fingerprint}]")

    if dry_run:
        return

    applied = 0
    for action in actions:
        if action.kind == "create_thread":
            client.create_thread(pr_id, action.payload)
            applied += 1
        elif action.kind == "reopen_thread":
            client.update_thread(pr_id, action.payload["threadId"], {"status": action.payload["status"]})
            applied += 1
        elif action.kind == "close_thread":
            client.update_thread(pr_id, action.payload["threadId"], {"status": action.payload["status"]})
            applied += 1
        elif action.kind == "add_comment":
            client.create_comment(pr_id, action.payload["threadId"], action.payload["content"])
            applied += 1

    print(f"Applied actions: {applied}")


if __name__ == "__main__":
    app()
