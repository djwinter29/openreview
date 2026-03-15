from __future__ import annotations

from pathlib import Path

import typer
from rich import print

from openreview import __version__
from openreview.application.commands.run_review import execute_run
from openreview.application.commands.sync_findings import execute_sync
from openreview.application.services.finding_pipeline import parse_findings_payload as _parse_findings_payload
from openreview.application.services.sync_orchestrator import print_summary as _print_summary
from openreview.domain.services.finding_filter_service import (
    SEVERITY_RANK,
    apply_hunk_mapping as _apply_hunk_mapping,
    cap_per_file as _cap_per_file,
    filter_findings as _filter_findings,
    path_allowed as _path_allowed,
)

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


@app.command()
def sync(
    pr_id: int = typer.Option(..., help="PR ID/number"),
    findings_file: Path = typer.Option(..., exists=True, help="Path to findings JSON"),
    provider: str = typer.Option("azure", help="azure|github|gitlab"),
    organization: str | None = typer.Option(None, help="Azure DevOps organization"),
    project: str | None = typer.Option(None, help="Azure DevOps project"),
    repository_id: str | None = typer.Option(None, help="Azure DevOps repository id"),
    pat: str | None = typer.Option(None, help="Azure DevOps PAT"),
    github_owner: str | None = typer.Option(None, help="GitHub owner/org"),
    github_repo: str | None = typer.Option(None, help="GitHub repository"),
    github_token: str | None = typer.Option(None, help="GitHub token"),
    gitlab_project_id: str | None = typer.Option(None, help="GitLab project id (url-encoded path or numeric id)"),
    gitlab_token: str | None = typer.Option(None, help="GitLab token"),
    gitlab_base_url: str = typer.Option("https://gitlab.com/api/v4", help="GitLab API base URL"),
    dry_run: bool = typer.Option(False, help="Only print planned actions"),
    summary_json: bool = typer.Option(False, "--summary-json", help="Print summary as JSON"),
) -> None:
    execute_sync(
        pr_id=pr_id,
        findings_file=findings_file,
        provider=provider,
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
        gitlab_project_id=gitlab_project_id,
        gitlab_token=gitlab_token,
        gitlab_base_url=gitlab_base_url,
        dry_run=dry_run,
        summary_json=summary_json,
    )


@app.command()
def run(
    pr_id: int = typer.Option(..., help="PR ID/number"),
    repo_root: Path = typer.Option(Path("."), help="Checked-out repo root"),
    base_ref: str = typer.Option("origin/main", help="Base ref for hunk diff mapping"),
    config_file: Path = typer.Option(Path(".openreview.yml"), help="Path to .openreview.yml"),
    provider: str = typer.Option("azure", help="azure|github|gitlab"),
    organization: str | None = typer.Option(None, help="Azure DevOps organization"),
    project: str | None = typer.Option(None, help="Azure DevOps project"),
    repository_id: str | None = typer.Option(None, help="Azure DevOps repository id"),
    pat: str | None = typer.Option(None, help="Azure DevOps PAT"),
    github_owner: str | None = typer.Option(None, help="GitHub owner/org"),
    github_repo: str | None = typer.Option(None, help="GitHub repository"),
    github_token: str | None = typer.Option(None, help="GitHub token"),
    gitlab_project_id: str | None = typer.Option(None, help="GitLab project id (url-encoded path or numeric id)"),
    gitlab_token: str | None = typer.Option(None, help="GitLab token"),
    gitlab_base_url: str = typer.Option("https://gitlab.com/api/v4", help="GitLab API base URL"),
    ai_provider: str = typer.Option("openai", help="openai|claude|deepseek"),
    ai_api_key: str | None = typer.Option(None, help="Generic AI API key for selected ai-provider"),
    ai_base_url: str | None = typer.Option(None, help="Optional AI base URL override"),
    ai_model: str = typer.Option("gpt-4.1-mini", help="AI model name"),
    openai_api_key: str | None = typer.Option(None, help="OpenAI API key (legacy option)"),
    max_files: int = typer.Option(25, help="Max changed files to review"),
    dry_run: bool = typer.Option(False, help="Only print planned actions"),
    summary_json: bool = typer.Option(False, "--summary-json", help="Print summary as JSON"),
) -> None:
    execute_run(
        pr_id=pr_id,
        repo_root=repo_root,
        base_ref=base_ref,
        config_file=config_file,
        provider=provider,
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
        github_owner=github_owner,
        github_repo=github_repo,
        github_token=github_token,
        gitlab_project_id=gitlab_project_id,
        gitlab_token=gitlab_token,
        gitlab_base_url=gitlab_base_url,
        ai_provider=ai_provider,
        ai_api_key=ai_api_key,
        ai_base_url=ai_base_url,
        ai_model=ai_model,
        openai_api_key=openai_api_key,
        max_files=max_files,
        dry_run=dry_run,
        summary_json=summary_json,
    )


if __name__ == "__main__":
    app()
