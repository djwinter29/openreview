"""! Application command for end-to-end review execution."""

from __future__ import annotations

from pathlib import Path

import typer

from openreview.application.services.review_orchestrator import execute_review
from openreview.application.services.sync_orchestrator import print_summary, sync_with_provider
from openreview.config import load_config
from openreview.ports.model import (
    ModelCallError,
    ModelConfigError,
    ModelRateLimitError,
    ReviewModelContractError,
    ReviewModelGateway,
)
from openreview.ports.scm import ChangedPathCollector, SyncExecutor


def execute_run(
    *,
    pr_id: int,
    repo_root: Path,
    base_ref: str,
    config_file: Path,
    max_files: int,
    dry_run: bool,
    summary_json: bool,
    changed_path_collector: ChangedPathCollector,
    sync_executor: SyncExecutor,
    review_model: ReviewModelGateway,
) -> None:
    """! Execute the full review workflow for a pull request.

    The workflow loads review policy, collects changed files, invokes the review
    agent, filters and maps findings, and then synchronizes the resulting
    comments with the configured SCM provider.
    """

    cfg = load_config(config_file)

    try:
        review_result = execute_review(
            pr_id=pr_id,
            repo_root=repo_root,
            base_ref=base_ref,
            config=cfg,
            changed_path_collector=changed_path_collector,
            review_model=review_model,
            max_files=max_files,
        )
    except ReviewModelContractError as err:
        raise typer.BadParameter(f"review model returned invalid structured output: {err}") from err
    except ModelRateLimitError as err:
        raise typer.BadParameter(f"review model rate limited the request: {err}") from err
    except (ModelConfigError, ModelCallError) as err:
        raise typer.BadParameter(f"review model request failed: {err}") from err

    planned, summary = sync_with_provider(
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
