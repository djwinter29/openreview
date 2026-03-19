"""! Application command for end-to-end review execution."""

from __future__ import annotations

from pathlib import Path

from openreview.application.services.review_orchestrator import execute_review
from openreview.application.services.sync_orchestrator import print_summary, sync_with_provider
from openreview.config import load_config
from openreview.ports.model import ModelPort
from openreview.ports.scm import ChangedPathCollector, ProviderOptions, SyncExecutor


def execute_run(
    *,
    pr_id: int,
    repo_root: Path,
    base_ref: str,
    config_file: Path,
    ai_provider: str,
    ai_base_url: str | None,
    ai_model: str,
    max_files: int,
    dry_run: bool,
    summary_json: bool,
    provider_options: ProviderOptions,
    changed_path_collector: ChangedPathCollector,
    sync_executor: SyncExecutor,
    model_gateway: ModelPort,
    api_key: str,
) -> None:
    """! Execute the full review workflow for a pull request.

    The workflow loads review policy, collects changed files, invokes the review
    agent, filters and maps findings, and then synchronizes the resulting
    comments with the configured SCM provider.
    """

    cfg = load_config(config_file)

    review_result = execute_review(
        pr_id=pr_id,
        repo_root=repo_root,
        base_ref=base_ref,
        config=cfg,
        provider_options=provider_options,
        changed_path_collector=changed_path_collector,
        model_gateway=model_gateway,
        api_key=api_key,
        ai_provider=ai_provider,
        ai_model=ai_model,
        ai_base_url=ai_base_url,
        max_files=max_files,
    )

    planned, summary = sync_with_provider(
        provider_options,
        pr_id,
        review_result.findings,
        dry_run=dry_run,
        sync_executor=sync_executor,
    )
    print_summary(
        raw_findings=review_result.raw_findings,
        filtered_findings=len(review_result.findings),
        planned_actions=planned,
        summary=summary,
        summary_json=summary_json,
    )
