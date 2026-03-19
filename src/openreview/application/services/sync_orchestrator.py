"""! Helpers for provider option resolution and sync summary output."""

from __future__ import annotations

import json

import typer
from rich import print

from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.scm import ProviderOptions, SyncExecutionError, SyncExecutor, SyncSummary


def env_or_option(value: str | None, env_name: str) -> str:
    """! Resolve a required value from a CLI option or environment variable."""

    import os

    if value:
        return value
    env_val = os.getenv(env_name)
    if env_val:
        return env_val
    raise typer.BadParameter(f"Missing value. Provide --{env_name.lower().replace('_', '-')} or set {env_name}")


def provider_options(
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
) -> ProviderOptions:
    """! Build normalized SCM provider options from CLI inputs and environment."""

    return ProviderOptions(
        provider=provider,
        organization=env_or_option(organization, "AZDO_ORG") if provider == "azure" else organization,
        project=env_or_option(project, "AZDO_PROJECT") if provider == "azure" else project,
        repository_id=env_or_option(repository_id, "AZDO_REPO_ID") if provider == "azure" else repository_id,
        pat=env_or_option(pat, "AZDO_PAT") if provider == "azure" else pat,
        github_owner=env_or_option(github_owner, "GITHUB_OWNER") if provider == "github" else github_owner,
        github_repo=env_or_option(github_repo, "GITHUB_REPO") if provider == "github" else github_repo,
        github_token=env_or_option(github_token, "GITHUB_TOKEN") if provider == "github" else github_token,
        gitlab_project_id=env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID") if provider == "gitlab" else gitlab_project_id,
        gitlab_token=env_or_option(gitlab_token, "GITLAB_TOKEN") if provider == "gitlab" else gitlab_token,
        gitlab_base_url=gitlab_base_url,
    )


def model_api_key(provider: str, ai_api_key: str | None, openai_api_key: str | None) -> str:
    """! Resolve the API key required for the selected model provider."""

    if ai_api_key:
        return ai_api_key
    if provider == "openai":
        return env_or_option(openai_api_key, "OPENAI_API_KEY")
    if provider in {"claude", "anthropic"}:
        return env_or_option(None, "ANTHROPIC_API_KEY")
    if provider == "deepseek":
        return env_or_option(None, "DEEPSEEK_API_KEY")
    raise typer.BadParameter("ai-provider must be one of: openai|claude|deepseek")


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
    options: ProviderOptions,
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
        actions, summary = sync_executor.sync(options, pr_id, findings, dry_run=dry_run)
    except SyncExecutionError as err:
        raise typer.BadParameter(str(err)) from err

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        fingerprint = getattr(action, "fingerprint", "n/a")
        print(f"- {action.kind} [{fingerprint}]")

    print(f"Applied actions: {summary.applied}")
    return len(actions), summary
