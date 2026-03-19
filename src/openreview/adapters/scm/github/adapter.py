from __future__ import annotations

from dataclasses import dataclass

from openreview.adapters.scm.github.client import GitHubClient
from openreview.adapters.scm.github.sync import (
    build_summary_comment,
    find_existing_summary_comment,
    normalize_github_comments,
    plan_github_sync,
)
from openreview.domain.entities.sync_action import CloseFindingComment, CreateFindingComment, RefreshFindingComment, SyncAction
from openreview.ports.scm import ExistingReviewComment, SyncSummary


@dataclass
class GitHubProvider:
    client: GitHubClient

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]:
        return normalize_github_comments(self.client.get_review_comments(pr_id) + self.client.get_issue_comments(pr_id))

    def plan(self, findings, existing: list[ExistingReviewComment]):
        return plan_github_sync(findings, existing)

    def apply(self, pr_id: int, actions: list[SyncAction], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for action in actions if isinstance(action, CreateFindingComment))
        updated = sum(1 for action in actions if isinstance(action, RefreshFindingComment))
        closed = sum(1 for action in actions if isinstance(action, CloseFindingComment))
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        pr = self.client.get_pull_request(pr_id)
        head_sha = ((pr.get("head") or {}).get("sha"))

        applied = 0
        for action in actions:
            if isinstance(action, CreateFindingComment):
                target = action.target
                assert target is not None
                try:
                    self.client.create_review_comment(
                        pr_number=pr_id,
                        body=action.body,
                        commit_id=head_sha,
                        path=target.path.lstrip("/"),
                        line=target.line,
                    )
                except Exception:
                    self.client.create_issue_comment(pr_id, action.body)
            else:
                try:
                    self.client.update_review_comment(action.comment_id, action.body)
                except Exception:
                    self.client.update_issue_comment(action.comment_id, action.body)
            applied += 1

        summary = build_summary_comment(created=created, updated=updated, closed=closed, total_findings=created + updated)
        old = find_existing_summary_comment(self.client.get_issue_comments(pr_id))
        if old:
            self.client.update_issue_comment(old["id"], summary)
        else:
            self.client.create_issue_comment(pr_id, summary)

        return SyncSummary(planned=len(actions), applied=applied, created=created, updated=updated, closed=closed)
