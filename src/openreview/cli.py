from __future__ import annotations

import json
import os
from pathlib import Path

import typer
from rich import print

from openreview import __version__
from openreview.ai_reviewer import ChangedFile, review_changed_files
from openreview.providers.azure.client import AzureDevOpsClient
from openreview.config import load_config
from openreview.diff_mapper import changed_hunks, nearest_line_or_none
from openreview.providers.github.client import GitHubClient
from openreview.providers.github.sync import build_summary_comment, find_existing_summary_comment, plan_github_sync
from openreview.providers.gitlab.client import GitLabClient
from openreview.providers.gitlab.sync import build_summary_note, find_existing_summary_note, plan_gitlab_sync
from openreview.review_sync import ReviewFinding, build_summary_content, find_summary_thread, plan_sync

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


def _apply_actions(client: AzureDevOpsClient, pr_id: int, actions: list) -> int:
    applied = 0
    for action in actions:
        if action.kind == "create_thread":
            client.create_thread(pr_id, action.payload)
            applied += 1
        elif action.kind == "reopen_thread":
            client.update_thread(pr_id, action.payload["threadId"], {"status": action.payload["status"]})
            applied += 1
        elif action.kind == "close_thread":
            client.update_thread(pr_id, action.payload["threadId"], {"status": action.payload["status"]})
            applied += 1
        elif action.kind == "add_comment":
            client.create_comment(pr_id, action.payload["threadId"], action.payload["content"])
            applied += 1
    return applied


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
    # higher severity/confidence first within each file
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

    if provider == "gitlab":
        gitlab_project_id = _env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID")
        gitlab_token = _env_or_option(gitlab_token, "GITLAB_TOKEN")
        gl = GitLabClient(project_id=gitlab_project_id, token=gitlab_token, base_url=gitlab_base_url)

        existing_notes = gl.get_mr_notes(pr_id)
        actions = plan_gitlab_sync(findings, existing_notes)

        print(f"Planned actions: {len(actions)}")
        for action in actions:
            print(f"- {action.kind} [{action.fingerprint}]")

        if dry_run:
            return

        applied = 0
        created = updated = closed = 0
        for action in actions:
            if action.kind == "create_note":
                gl.create_mr_note(pr_id, action.payload["body"])
                created += 1
            else:
                gl.update_mr_note(pr_id, action.payload["note_id"], action.payload["body"])
                if action.kind == "close_note":
                    closed += 1
                else:
                    updated += 1
            applied += 1

        summary = build_summary_note(created=created, updated=updated, closed=closed, total_findings=len(findings))
        summary_existing = find_existing_summary_note(gl.get_mr_notes(pr_id))
        if summary_existing:
            gl.update_mr_note(pr_id, summary_existing["id"], summary)
        else:
            gl.create_mr_note(pr_id, summary)

        print(f"Applied actions: {applied}")
        return

    if provider == "gitlab":
        gitlab_project_id = _env_or_option(gitlab_project_id, "GITLAB_PROJECT_ID")
        gitlab_token = _env_or_option(gitlab_token, "GITLAB_TOKEN")
        gl = GitLabClient(project_id=gitlab_project_id, token=gitlab_token, base_url=gitlab_base_url)
        import subprocess
        diff_out = subprocess.check_output([
            "git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"
        ], text=True)
        changed_paths = ["/" + p.strip() for p in diff_out.splitlines() if p.strip()]
    elif provider == "github":
        github_owner = _env_or_option(github_owner, "GITHUB_OWNER")
        github_repo = _env_or_option(github_repo, "GITHUB_REPO")
        github_token = _env_or_option(github_token, "GITHUB_TOKEN")

        gh = GitHubClient(owner=github_owner, repo=github_repo, token=github_token)
        existing_comments = gh.get_review_comments(pr_id) + gh.get_issue_comments(pr_id)
        actions = plan_github_sync(findings, existing_comments)

        print(f"Planned actions: {len(actions)}")
        for action in actions:
            print(f"- {action.kind} [{action.fingerprint}]")

        if dry_run:
            return

        applied = 0
        created = updated = closed = 0
        pr = gh.get_pull_request(pr_id)
        head_sha = ((pr.get("head") or {}).get("sha"))
        for action in actions:
            if action.kind == "create_review_comment":
                try:
                    gh.create_review_comment(
                        pr_number=pr_id,
                        body=action.payload["body"],
                        commit_id=head_sha,
                        path=action.payload["path"],
                        line=action.payload["line"],
                    )
                except Exception:
                    # fallback to issue comments when line-level placement fails
                    gh.create_issue_comment(pr_id, action.payload["body"])
                created += 1
                applied += 1
            elif action.kind in {"update_review_comment", "close_review_comment"}:
                try:
                    gh.update_review_comment(action.payload["comment_id"], action.payload["body"])
                except Exception:
                    gh.update_issue_comment(action.payload["comment_id"], action.payload["body"])
                if action.kind == "close_review_comment":
                    closed += 1
                else:
                    updated += 1
                applied += 1

        summary = build_summary_comment(created=created, updated=updated, closed=closed, total_findings=len(findings))
        summary_existing = find_existing_summary_comment(gh.get_issue_comments(pr_id))
        if summary_existing:
            gh.update_issue_comment(summary_existing["id"], summary)
        else:
            gh.create_issue_comment(pr_id, summary)

        print(f"Applied actions: {applied}")
        return

    organization = _env_or_option(organization, "AZDO_ORG")
    project = _env_or_option(project, "AZDO_PROJECT")
    repository_id = _env_or_option(repository_id, "AZDO_REPO_ID")
    pat = _env_or_option(pat, "AZDO_PAT")

    client = AzureDevOpsClient(
        organization=organization,
        project=project,
        repository_id=repository_id,
        pat=pat,
    )

    existing_threads = client.get_pull_request_threads(pr_id)
    actions = plan_sync(findings, existing_threads)

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {action.kind} [{action.fingerprint}]")

    if dry_run:
        return

    applied = _apply_actions(client, pr_id, actions)
    created = sum(1 for a in actions if a.kind == "create_thread")
    updated = sum(1 for a in actions if a.kind in {"add_comment", "reopen_thread"})
    closed = sum(1 for a in actions if a.kind == "close_thread")
    summary = build_summary_content(created=created, updated=updated, closed=closed, total_findings=len(findings))
    summary_thread = find_summary_thread(client.get_pull_request_threads(pr_id))
    if summary_thread:
        client.create_comment(pr_id, summary_thread["id"], summary)
    else:
        client.create_thread(
            pr_id,
            {
                "comments": [{"parentCommentId": 0, "content": summary, "commentType": 1}],
                "status": 1,
            },
        )
    print(f"Applied actions: {applied}")



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

    if provider == "github":
        github_owner = _env_or_option(github_owner, "GITHUB_OWNER")
        github_repo = _env_or_option(github_repo, "GITHUB_REPO")
        github_token = _env_or_option(github_token, "GITHUB_TOKEN")
        gh = GitHubClient(owner=github_owner, repo=github_repo, token=github_token)
        # for MVP, use local git diff as changed source in github mode
        import subprocess
        diff_out = subprocess.check_output([
            "git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}...HEAD"
        ], text=True)
        changed_paths = ["/" + p.strip() for p in diff_out.splitlines() if p.strip()]
    else:
        organization = _env_or_option(organization, "AZDO_ORG")
        project = _env_or_option(project, "AZDO_PROJECT")
        repository_id = _env_or_option(repository_id, "AZDO_REPO_ID")
        pat = _env_or_option(pat, "AZDO_PAT")
        client = AzureDevOpsClient(
            organization=organization,
            project=project,
            repository_id=repository_id,
            pat=pat,
        )
        changed_paths = client.get_changed_files_latest_iteration(pr_id)
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

    if provider == "gitlab":
        existing_notes = gl.get_mr_notes(pr_id)
        actions = plan_gitlab_sync(findings, existing_notes)
        print(f"Planned actions: {len(actions)}")
        for action in actions:
            print(f"- {action.kind} [{action.fingerprint}]")
        if dry_run:
            return
        applied = 0
        created = updated = closed = 0
        for action in actions:
            if action.kind == "create_note":
                gl.create_mr_note(pr_id, action.payload["body"])
                created += 1
            else:
                gl.update_mr_note(pr_id, action.payload["note_id"], action.payload["body"])
                if action.kind == "close_note":
                    closed += 1
                else:
                    updated += 1
            applied += 1

        summary = build_summary_note(created=created, updated=updated, closed=closed, total_findings=len(findings))
        summary_existing = find_existing_summary_note(gl.get_mr_notes(pr_id))
        if summary_existing:
            gl.update_mr_note(pr_id, summary_existing["id"], summary)
        else:
            gl.create_mr_note(pr_id, summary)

        print(f"Applied actions: {applied}")
        return

    if provider == "github":
        existing_comments = gh.get_review_comments(pr_id) + gh.get_issue_comments(pr_id)
        actions = plan_github_sync(findings, existing_comments)
        print(f"Planned actions: {len(actions)}")
        for action in actions:
            print(f"- {action.kind} [{action.fingerprint}]")
        if dry_run:
            return
        applied = 0
        created = updated = closed = 0
        pr = gh.get_pull_request(pr_id)
        head_sha = ((pr.get("head") or {}).get("sha"))
        for action in actions:
            if action.kind == "create_review_comment":
                try:
                    gh.create_review_comment(
                        pr_number=pr_id,
                        body=action.payload["body"],
                        commit_id=head_sha,
                        path=action.payload["path"],
                        line=action.payload["line"],
                    )
                except Exception:
                    gh.create_issue_comment(pr_id, action.payload["body"])
                created += 1
            elif action.kind in {"update_review_comment", "close_review_comment"}:
                try:
                    gh.update_review_comment(action.payload["comment_id"], action.payload["body"])
                except Exception:
                    gh.update_issue_comment(action.payload["comment_id"], action.payload["body"])
                if action.kind == "close_review_comment":
                    closed += 1
                else:
                    updated += 1
            applied += 1

        summary = build_summary_comment(created=created, updated=updated, closed=closed, total_findings=len(findings))
        summary_existing = find_existing_summary_comment(gh.get_issue_comments(pr_id))
        if summary_existing:
            gh.update_issue_comment(summary_existing["id"], summary)
        else:
            gh.create_issue_comment(pr_id, summary)

        print(f"Applied actions: {applied}")
        return

    existing_threads = client.get_pull_request_threads(pr_id)
    actions = plan_sync(findings, existing_threads)

    print(f"Planned actions: {len(actions)}")
    for action in actions:
        print(f"- {action.kind} [{action.fingerprint}]")

    if dry_run:
        return

    applied = _apply_actions(client, pr_id, actions)
    created = sum(1 for a in actions if a.kind == "create_thread")
    updated = sum(1 for a in actions if a.kind in {"add_comment", "reopen_thread"})
    closed = sum(1 for a in actions if a.kind == "close_thread")
    summary = build_summary_content(created=created, updated=updated, closed=closed, total_findings=len(findings))
    summary_thread = find_summary_thread(client.get_pull_request_threads(pr_id))
    if summary_thread:
        client.create_comment(pr_id, summary_thread["id"], summary)
    else:
        client.create_thread(
            pr_id,
            {
                "comments": [{"parentCommentId": 0, "content": summary, "commentType": 1}],
                "status": 1,
            },
        )
    print(f"Applied actions: {applied}")


if __name__ == "__main__":
    app()
