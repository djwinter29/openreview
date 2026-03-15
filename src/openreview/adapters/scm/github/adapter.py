from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openreview.adapters.scm.github.client import GitHubClient
from openreview.adapters.scm.github.sync import (
    build_summary_comment,
    find_existing_summary_comment,
    plan_github_sync,
)
from openreview.ports.scm import SyncSummary


@dataclass
class GitHubProvider:
    client: GitHubClient

    def list_existing(self, pr_id: int) -> list[dict[str, Any]]:
        return self.client.get_review_comments(pr_id) + self.client.get_issue_comments(pr_id)

    def plan(self, findings, existing):
        return plan_github_sync(findings, existing)

    def apply(self, pr_id: int, actions: list[Any], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for action in actions if action.kind == "create_review_comment")
        updated = sum(1 for action in actions if action.kind == "update_review_comment")
        closed = sum(1 for action in actions if action.kind == "close_review_comment")
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        pr = self.client.get_pull_request(pr_id)
        head_sha = ((pr.get("head") or {}).get("sha"))

        applied = 0
        for action in actions:
            if action.kind == "create_review_comment":
                try:
                    self.client.create_review_comment(
                        pr_number=pr_id,
                        body=action.payload["body"],
                        commit_id=head_sha,
                        path=action.payload["path"],
                        line=action.payload["line"],
                    )
                except Exception:
                    self.client.create_issue_comment(pr_id, action.payload["body"])
            else:
                try:
                    self.client.update_review_comment(action.payload["comment_id"], action.payload["body"])
                except Exception:
                    self.client.update_issue_comment(action.payload["comment_id"], action.payload["body"])
            applied += 1

        summary = build_summary_comment(created=created, updated=updated, closed=closed, total_findings=created + updated)
        old = find_existing_summary_comment(self.client.get_issue_comments(pr_id))
        if old:
            self.client.update_issue_comment(old["id"], summary)
        else:
            self.client.create_issue_comment(pr_id, summary)

        return SyncSummary(planned=len(actions), applied=applied, created=created, updated=updated, closed=closed)
