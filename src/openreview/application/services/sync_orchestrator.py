"""! Helpers for provider option resolution and sync summary output."""

from __future__ import annotations

import json

import typer
from rich import print

from openreview.application.errors import ApplicationExecutionError
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import sync_action_kind
from openreview.ports.scm import SyncExecutionError, SyncExecutor, SyncSummary


def summary_payload(*, raw_findings: int | None, filtered_findings: int | None, planned_actions: int, summary: SyncSummary) -> dict[str, int]:
    """! Convert sync results into a serializable summary dictionary."""

    payload: dict[str, int] = {
        "planned_actions": planned_actions,
        "applied_actions": summary.applied,
        "created": summary.created,
        "updated": summary.updated,
        "closed": summary.closed,
        "skipped": max(0, planned_actions - summary.applied),
    }
    if raw_findings is not None:
        payload["findings_raw"] = raw_findings
    if filtered_findings is not None:
        payload["findings_filtered"] = filtered_findings
    return payload


def print_summary(
    *,
    raw_findings: int | None,
    filtered_findings: int | None,
    planned_actions: int,
    summary: SyncSummary,
    summary_json: bool = False,
) -> None:
    """! Print sync results as either plain text or JSON."""

    payload = summary_payload(
        raw_findings=raw_findings,
        filtered_findings=filtered_findings,
        planned_actions=planned_actions,
        summary=summary,
    )
    if summary_json:
        typer.echo(json.dumps(payload, sort_keys=True))
        return

    print("openreview summary")
    if raw_findings is not None:
        print(f"- findings_raw: {raw_findings}")
    if filtered_findings is not None:
        print(f"- findings_filtered: {filtered_findings}")
    print(f"- planned_actions: {planned_actions}")
    print(f"- applied_actions: {summary.applied}")
    print(f"- created: {summary.created}")
    print(f"- updated: {summary.updated}")
    print(f"- closed: {summary.closed}")
    print(f"- skipped: {max(0, planned_actions - summary.applied)}")


def sync_with_provider(
    pr_id: int,
    findings: list[ReviewFinding],
    *,
    dry_run: bool,
    sync_executor: SyncExecutor,
) -> tuple[int, SyncSummary]:
    """! Execute provider sync and print the planned actions.

    @return A tuple containing the number of planned actions and the provider summary.
    """

    try:
        actions, summary = sync_executor.sync(pr_id, findings, dry_run=dry_run)
    except SyncExecutionError as err:
        raise ApplicationExecutionError(str(err)) from err

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {sync_action_kind(action)} [{action.fingerprint}]")

    print(f"Applied actions: {summary.applied}")
    return len(actions), summary
