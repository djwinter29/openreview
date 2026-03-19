from __future__ import annotations

from dataclasses import dataclass

from openreview.adapters.scm.azure_devops.client import AzureDevOpsClient
from openreview.adapters.scm.azure_devops.sync import (
    build_azure_summary,
    find_azure_summary_thread,
    normalize_azure_threads,
    plan_azure_sync,
)
from openreview.ports.scm import ExistingReviewComment, ProviderAction, SyncSummary


@dataclass
class AzureProvider:
    client: AzureDevOpsClient

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]:
        return normalize_azure_threads(self.client.get_pull_request_threads(pr_id))

    def plan(self, findings, existing: list[ExistingReviewComment]):
        return plan_azure_sync(findings, existing)

    def apply(self, pr_id: int, actions: list[ProviderAction], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for action in actions if action.kind == "create_thread")
        updated = sum(1 for action in actions if action.kind in {"add_comment", "reopen_thread"})
        closed = sum(1 for action in actions if action.kind == "close_thread")
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        applied = 0
        for action in actions:
            if action.kind == "create_thread":
                self.client.create_thread(pr_id, action.payload)
            elif action.kind in {"reopen_thread", "close_thread"}:
                self.client.update_thread(pr_id, action.payload["threadId"], {"status": action.payload["status"]})
            elif action.kind == "add_comment":
                self.client.create_comment(pr_id, action.payload["threadId"], action.payload["content"])
            applied += 1

        summary = build_azure_summary(created=created, updated=updated, closed=closed, total_findings=created + updated)
        existing = self.client.get_pull_request_threads(pr_id)
        thread = find_azure_summary_thread(existing)
        if thread:
            self.client.create_comment(pr_id, thread["id"], summary)
        else:
            self.client.create_thread(
                pr_id,
                {"comments": [{"parentCommentId": 0, "content": summary, "commentType": 1}], "status": 1},
            )

        return SyncSummary(planned=len(actions), applied=applied, created=created, updated=updated, closed=closed)
