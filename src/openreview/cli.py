from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import typer
from rich import print

from openreview import __version__
from openreview.ai_reviewer import ChangedFile, review_changed_files
from openreview.config import load_config
from openreview.diff_mapper import changed_hunks, nearest_line_or_none
from openreview.providers.azure import AzureDevOpsClient, AzureProvider
from openreview.providers.base import ReviewProvider
from openreview.providers.github import GitHubClient, GitHubProvider
from openreview.providers.gitlab import GitLabClient, GitLabProvider
from openreview.sync_core import ReviewFinding

app = typer.Typer(help="openreview - AI-assisted PR review automation")

SEVERITY_RANK = {"info": 1, "warning": 2, "error": 3}


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


def _filter_findings(findings: list[ReviewFinding], min_severity: str, min_confidence: float) -> list[ReviewFinding]:
    floor = SEVERITY_RANK.get(min_severity, 2)
    kept: list[ReviewFinding] = []
    seen: set[str] = set()
    for f in findings:
        if SEVERITY_RANK.get(f.severity, 2) < floor:
            continue
        if f.confidence < min_confidence:
            continue
        if f.fingerprint in seen:
            continue
        seen.add(f.fingerprint)
        kept.append(f)
    return kept


def _path_allowed(path: str, include_paths: list[str], exclude_paths: list[str]) -> bool:
    if include_paths and not any(path.startswith(p) for p in include_paths):
        return False
    if any(path.startswith(p) for p in exclude_paths):
        return False
    return True


def _apply_hunk_mapping(findings: list[ReviewFinding], hunks_by_file: dict[str, list], changed_lines_only: bool) -> list[ReviewFinding]:
    out: list[ReviewFinding] = []
    for f in findings:
        mapped = nearest_line_or_none(f.path, f.line, hunks_by_file)
        if mapped is None:
            if changed_lines_only:
                continue
            out.append(f)
            continue
        f.line = mapped
        out.append(f)
    return out


def _cap_per_file(findings: list[ReviewFinding], max_comments_per_file: int) -> list[ReviewFinding]:
    if max_comments_per_file <= 0:
        return findings
    counts: dict[str, int] = {}
    out: list[ReviewFinding] = []
    ranked = sorted(
        findings,
        key=lambda f: (f.path, -SEVERITY_RANK.get(f.severity, 2), -f.confidence, f.line),
    )
    for f in ranked:
        used = counts.get(f.path, 0)
        if used >= max_comments_per_file:
            continue
        counts[f.path] = used + 1
        out.append(f)
    return out


def _build_provider(
    *,
    provider: str,
    organization: str | None,
    project: str | None,
    repository_id: str | None,
    pat: str | None,
    github_owner: str | None,
    github_repo: str | None,
    github_token: str | None,
    gitlab_project_id: str | None,
    gitlab_token: str | None,
    gitlab_base_url: str,
) -> ReviewProvider:
    if provider == "github":
        return GitHubProvider(
            GitHubClient(
                owner=_env_or_option(github_owner, "GITHUB_OWNER"),
                repo=_env_or_option(github_repo, "GITHUB_REPO"),
                token=_env_or_option(github_token, "GITHUB_TOKEN"),
            )
        )

    if provider == "gitlab":
        return GitLabProvider(
            GitLabClient(
                project_id=_env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID"),
                token=_env_or_option(gitlab_token, "GITLAB_TOKEN"),
                base_url=gitlab_base_url,
            )
        )

    if provider != "azure":
        raise typer.BadParameter("provider must be one of: azure|github|gitlab")

    return AzureProvider(
        AzureDevOpsClient(
            organization=_env_or_option(organization, "AZDO_ORG"),
            project=_env_or_option(project, "AZDO_PROJECT"),
            repository_id=_env_or_option(repository_id, "AZDO_REPO_ID"),
            pat=_env_or_option(pat, "AZDO_PAT"),
        )
    )


def _sync_with_provider(provider: ReviewProvider, pr_id: int, findings: list[ReviewFinding], *, dry_run: bool) -> None:
    existing = provider.list_existing(pr_id)
    actions = provider.plan(findings, existing)

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {action.kind} [{action.fingerprint}]")

    summary = provider.apply(pr_id, actions, dry_run=dry_run)
    print(f"Applied actions: {summary.applied}")


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
) -> None:
    findings_raw = json.loads(findings_file.read_text())
    findings = [ReviewFinding(**item) for item in findings_raw]

    provider_impl = _build_provider(
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
    )
    _sync_with_provider(provider_impl, pr_id, findings, dry_run=dry_run)


@app.command()
def run(
    pr_id: int = typer.Option(..., help="PR ID/number"),
    repo_root: Path = typer.Option(Path('.'), help="Checked-out repo root"),
    base_ref: str = typer.Option("origin/main", help="Base ref for hunk diff mapping"),
    config_file: Path = typer.Option(Path('.openreview.yml'), help="Path to .openreview.yml"),
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
    openai_api_key: str | None = typer.Option(None, help="OpenAI API key"),
    openai_model: str = typer.Option("gpt-4.1-mini", help="OpenAI model"),
    max_files: int = typer.Option(25, help="Max changed files to review"),
    dry_run: bool = typer.Option(False, help="Only print planned actions"),
) -> None:
    cfg = load_config(config_file)
    openai_api_key = _env_or_option(openai_api_key, "OPENAI_API_KEY")

    if provider == "azure":
        az = AzureDevOpsClient(
            organization=_env_or_option(organization, "AZDO_ORG"),
            project=_env_or_option(project, "AZDO_PROJECT"),
            repository_id=_env_or_option(repository_id, "AZDO_REPO_ID"),
            pat=_env_or_option(pat, "AZDO_PAT"),
        )
        changed_paths = az.get_changed_files_latest_iteration(pr_id)
    else:
        diff_out = subprocess.check_output([
            "git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"
        ], text=True)
        changed_paths = ["/" + p.strip() for p in diff_out.splitlines() if p.strip()]

    changed_paths = [p for p in changed_paths if _path_allowed(p, cfg.rules.include_paths, cfg.rules.exclude_paths)]
    files = [ChangedFile(path=p) for p in changed_paths[:max_files]]
    print(f"Changed files considered: {len(files)}")

    findings = review_changed_files(
        api_key=openai_api_key,
        model=openai_model,
        files=files,
        repo_root=repo_root,
    )
    print(f"AI findings (raw): {len(findings)}")

    hunks = changed_hunks(repo_root, base_ref)
    findings = _apply_hunk_mapping(findings, hunks, cfg.rules.changed_lines_only)
    findings = _filter_findings(findings, cfg.rules.min_severity, cfg.rules.min_confidence)
    findings = _cap_per_file(findings, cfg.rules.max_comments_per_file)
    findings = findings[: cfg.rules.max_comments]
    print(f"AI findings (filtered): {len(findings)}")

    provider_impl = _build_provider(
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
    )
    _sync_with_provider(provider_impl, pr_id, findings, dry_run=dry_run)


if __name__ == "__main__":
    app()
