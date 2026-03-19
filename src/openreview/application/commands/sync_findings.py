"""! Application command for syncing precomputed findings."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path

import typer

from openreview.application.services.finding_pipeline import parse_findings_payload
from openreview.application.services.sync_orchestrator import print_summary, sync_with_provider
from openreview.ports.scm import ProviderOptions, SyncExecutor


def execute_sync(
    *,
    pr_id: int,
    findings_file: Path,
    dry_run: bool,
    summary_json: bool,
    provider_options: ProviderOptions,
    sync_executor: SyncExecutor,
) -> None:
    """! Load findings from disk, validate them, and sync them to a provider.

    @param pr_id Pull request or merge request identifier.
    @param findings_file Path to a JSON array of finding objects.
    @param provider Selected SCM provider name.
    @param dry_run When true, only print planned actions.
    @param summary_json When true, print a machine-readable summary.
    """

    try:
        findings_raw = json.loads(findings_file.read_text())
    except JSONDecodeError as err:
        raise typer.BadParameter("findings file must contain valid JSON") from err

    findings = parse_findings_payload(findings_raw)
    planned, summary = sync_with_provider(
        provider_options,
        pr_id,
        findings,
        dry_run=dry_run,
        sync_executor=sync_executor,
    )
    print_summary(
        raw_findings=None,
        filtered_findings=len(findings),
        planned_actions=planned,
        summary=summary,
        summary_json=summary_json,
    )
