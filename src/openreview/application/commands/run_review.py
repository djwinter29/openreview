"""! Application command for end-to-end review execution."""

from __future__ import annotations

from pathlib import Path

from openreview.adapters.scm.runtime import DefaultChangedPathCollector, DefaultSyncExecutor
from openreview.application.services.review_orchestrator import execute_review
from openreview.application.services.sync_orchestrator import (
    model_api_key,
    print_summary,
    provider_options,
    sync_with_provider,
)
from openreview.config import load_config


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
    """! Execute the full review workflow for a pull request.

    The workflow loads review policy, collects changed files, invokes the review
    agent, filters and maps findings, and then synchronizes the resulting
    comments with the configured SCM provider.
    """

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

    review_result = execute_review(
        pr_id=pr_id,
        repo_root=repo_root,
        base_ref=base_ref,
        config=cfg,
        provider_options=options,
        changed_path_collector=DefaultChangedPathCollector(),
        api_key=selected_key,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_base_url=ai_base_url,
        max_files=max_files,
    )

    planned, summary = sync_with_provider(
        options,
        pr_id,
        review_result.findings,
        dry_run=dry_run,
        sync_executor=DefaultSyncExecutor(),
    )
    print_summary(
        raw_findings=review_result.raw_findings,
        filtered_findings=len(review_result.findings),
        planned_actions=planned,
        summary=summary,
        summary_json=summary_json,
    )
