from __future__ import annotations

from dataclasses import dataclass

from openreview.adapters.scm.azure_devops.client import AzureDevOpsClient
from openreview.adapters.scm.azure_devops.sync import (
    build_azure_summary,
    find_azure_summary_thread,
    normalize_azure_threads,
)
from openreview.domain.entities.sync_action import CloseFindingComment, CreateInlineFindingComment, RefreshFindingComment, SyncAction
from openreview.ports.scm import ExistingReviewComment, SyncSummary


@dataclass
class AzureProvider:
    client: AzureDevOpsClient

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]:
        return normalize_azure_threads(self.client.get_pull_request_threads(pr_id))

    def apply(self, pr_id: int, actions: list[SyncAction], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for action in actions if isinstance(action, CreateInlineFindingComment))
        updated = sum(1 for action in actions if isinstance(action, RefreshFindingComment))
        closed = sum(1 for action in actions if isinstance(action, CloseFindingComment))
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        applied = 0
        for action in actions:
            if isinstance(action, CreateInlineFindingComment):
                self.client.create_thread(
                    pr_id,
                    {
                        "comments": [{"parentCommentId": 0, "content": action.body, "commentType": 1}],
                        "status": 1,
                        "threadContext": {
                            "filePath": action.target.path,
                            "rightFileStart": {"line": action.target.line, "offset": 1},
                            "rightFileEnd": {"line": action.target.line, "offset": 1},
                        },
                    },
                )
            elif isinstance(action, RefreshFindingComment):
                if action.reopen:
                    self.client.update_thread(pr_id, action.comment_id, {"status": 1})
                self.client.create_comment(pr_id, action.comment_id, action.body)
            elif isinstance(action, CloseFindingComment):
                self.client.update_thread(pr_id, action.comment_id, {"status": 4})
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
