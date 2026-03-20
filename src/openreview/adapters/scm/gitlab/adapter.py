from __future__ import annotations

from dataclasses import dataclass

from openreview.adapters.scm.gitlab.client import GitLabClient
from openreview.adapters.scm.gitlab.sync import (
    build_summary_note,
    find_existing_summary_note,
    normalize_gitlab_notes,
)
from openreview.domain.entities.sync_action import CloseFindingComment, CreateGeneralFindingComment, CreateInlineFindingComment, RefreshFindingComment, SyncAction
from openreview.ports.scm import ExistingReviewComment, SyncSummary


@dataclass
class GitLabProvider:
    client: GitLabClient

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]:
        return normalize_gitlab_notes(self.client.get_mr_notes(pr_id))

    def apply(self, pr_id: int, actions: list[SyncAction], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for action in actions if isinstance(action, (CreateInlineFindingComment, CreateGeneralFindingComment)))
        updated = sum(1 for action in actions if isinstance(action, RefreshFindingComment))
        closed = sum(1 for action in actions if isinstance(action, CloseFindingComment))
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        applied = 0
        for action in actions:
            if isinstance(action, (CreateInlineFindingComment, CreateGeneralFindingComment)):
                self.client.create_mr_note(pr_id, action.body)
            else:
                self.client.update_mr_note(pr_id, action.comment_id, action.body)
            applied += 1

        summary = build_summary_note(created=created, updated=updated, closed=closed, total_findings=created + updated)
        old = find_existing_summary_note(self.client.get_mr_notes(pr_id))
        if old:
            self.client.update_mr_note(pr_id, old["id"], summary)
        else:
            self.client.create_mr_note(pr_id, summary)

        return SyncSummary(planned=len(actions), applied=applied, created=created, updated=updated, closed=closed)
