from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich import print

from openreview.adapters.scm.azure_devops.client import AzureDevOpsClient
from openreview.application.services.sync_orchestrator import (
    model_api_key,
    print_summary,
    provider_options,
    sync_with_provider,
)
from openreview.config import load_config
from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.services.finding_filter_service import (
    apply_hunk_mapping,
    cap_per_file,
    filter_findings,
    path_allowed,
)
from openreview.domain.services.line_mapping_service import changed_hunks
from openreview.reviewers.agents.general_code_review import review_changed_files


def _git_changed_paths(repo_root: Path, base_ref: str) -> list[str]:
    try:
        diff_out = subprocess.check_output(
            ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"],
            text=True,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as err:
        output = (err.output or "").strip()
        msg = f"Unable to diff against base ref '{base_ref}'."
        if output:
            msg = f"{msg} git said: {output}"
        raise typer.BadParameter(msg) from err
    return ["/" + p.strip() for p in diff_out.splitlines() if p.strip()]


def execute_run(
    *,
    pr_id: int,
    repo_root: Path,
    base_ref: str,
    config_file: Path,
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
    ai_provider: str,
    ai_api_key: str | None,
    ai_base_url: str | None,
    ai_model: str,
    openai_api_key: str | None,
    max_files: int,
    dry_run: bool,
    summary_json: bool,
) -> None:
    cfg = load_config(config_file)
    selected_key = model_api_key(ai_provider, ai_api_key, openai_api_key)
    options = provider_options(
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

    if provider == "azure":
        az = AzureDevOpsClient(
            organization=options.organization,
            project=options.project,
            repository_id=options.repository_id,
            pat=options.pat,
        )
        changed_paths = az.get_changed_files_latest_iteration(pr_id)
    else:
        changed_paths = _git_changed_paths(repo_root, base_ref)

    changed_paths = [p for p in changed_paths if path_allowed(p, cfg.rules.include_paths, cfg.rules.exclude_paths)]
    files = [ChangedFile(path=p) for p in changed_paths[:max_files]]
    print(f"Changed files considered: {len(files)}")

    findings = review_changed_files(
        api_key=selected_key,
        model=ai_model,
        api_provider=ai_provider,
        api_base_url=ai_base_url,
        files=files,
        repo_root=repo_root,
    )
    raw_findings = len(findings)
    print(f"AI findings (raw): {raw_findings}")

    try:
        hunks = changed_hunks(repo_root, base_ref)
    except subprocess.CalledProcessError as err:
        raise typer.BadParameter(f"Unable to map changed hunks against '{base_ref}'.") from err

    findings = apply_hunk_mapping(findings, hunks, cfg.rules.changed_lines_only)
    findings = filter_findings(findings, cfg.rules.min_severity, cfg.rules.min_confidence)
    findings = cap_per_file(findings, cfg.rules.max_comments_per_file)
    findings = findings[: cfg.rules.max_comments]
    print(f"AI findings (filtered): {len(findings)}")

    planned, summary = sync_with_provider(options, pr_id, findings, dry_run=dry_run)
    print_summary(
        raw_findings=raw_findings,
        filtered_findings=len(findings),
        planned_actions=planned,
        summary=summary,
        summary_json=summary_json,
    )
