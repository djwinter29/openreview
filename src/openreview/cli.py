from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from openreview import __version__
from openreview.ai_reviewer import ChangedFile, review_changed_files
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
    raise typer.BadParameter(f"Missing value. Provide --{env_name.lower().replace('_', '-')} or set {env_name}")


def _apply_actions(client: AzureDevOpsClient, pr_id: int, actions: list) -> int:
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
    return applied


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

    applied = _apply_actions(client, pr_id, actions)
    print(f"Applied actions: {applied}")


@app.command()
def run(
    pr_id: int = typer.Option(..., help="Azure DevOps PR ID"),
    repo_root: Path = typer.Option(Path('.'), help="Checked-out repo root"),
    organization: str | None = typer.Option(None, help="Azure DevOps organization"),
    project: str | None = typer.Option(None, help="Azure DevOps project"),
    repository_id: str | None = typer.Option(None, help="Azure DevOps repository id"),
    pat: str | None = typer.Option(None, help="Azure DevOps PAT"),
    openai_api_key: str | None = typer.Option(None, help="OpenAI API key"),
    openai_model: str = typer.Option("gpt-4.1-mini", help="OpenAI model"),
    max_files: int = typer.Option(25, help="Max changed files to review"),
    dry_run: bool = typer.Option(False, help="Only print planned actions"),
) -> None:
    organization = _env_or_option(organization, "AZDO_ORG")
    project = _env_or_option(project, "AZDO_PROJECT")
    repository_id = _env_or_option(repository_id, "AZDO_REPO_ID")
    pat = _env_or_option(pat, "AZDO_PAT")
    openai_api_key = _env_or_option(openai_api_key, "OPENAI_API_KEY")

    client = AzureDevOpsClient(
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
    )

    changed_paths = client.get_changed_files_latest_iteration(pr_id)
    files = [ChangedFile(path=p) for p in changed_paths[:max_files]]
    print(f"Changed files considered: {len(files)}")

    findings = review_changed_files(
        api_key=openai_api_key,
        model=openai_model,
        files=files,
        repo_root=repo_root,
    )
    print(f"AI findings: {len(findings)}")

    existing_threads = client.get_pull_request_threads(pr_id)
    actions = plan_sync(findings, existing_threads)

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {action.kind} [{action.fingerprint}]")

    if dry_run:
        return

    applied = _apply_actions(client, pr_id, actions)
    print(f"Applied actions: {applied}")


if __name__ == "__main__":
    app()
