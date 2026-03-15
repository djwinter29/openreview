from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

import typer

from openreview.application.services.finding_pipeline import parse_findings_payload
from openreview.application.services.sync_orchestrator import (
    print_summary,
    provider_options,
    sync_with_provider,
)


def execute_sync(
    *,
    pr_id: int,
    findings_file: Path,
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
    dry_run: bool,
    summary_json: bool,
) -> None:
    try:
        findings_raw = json.loads(findings_file.read_text())
    except JSONDecodeError as err:
        raise typer.BadParameter("findings file must contain valid JSON") from err

    findings = parse_findings_payload(findings_raw)
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
    planned, summary = sync_with_provider(options, pr_id, findings, dry_run=dry_run)
    print_summary(
        raw_findings=None,
        filtered_findings=len(findings),
        planned_actions=planned,
        summary=summary,
        summary_json=summary_json,
    )
