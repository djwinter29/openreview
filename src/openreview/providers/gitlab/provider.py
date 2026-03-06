from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openreview.providers.base import SyncSummary
from openreview.providers.gitlab.client import GitLabClient
from openreview.providers.gitlab.sync import (
    build_summary_note,
    find_existing_summary_note,
    plan_gitlab_sync,
)


@dataclass
class GitLabProvider:
    client: GitLabClient

    def list_existing(self, pr_id: int) -> list[dict[str, Any]]:
        return self.client.get_mr_notes(pr_id)

    def plan(self, findings, existing):
        return plan_gitlab_sync(findings, existing)

    def apply(self, pr_id: int, actions: list[Any], *, dry_run: bool = False) -> SyncSummary:
        created = sum(1 for a in actions if a.kind == "create_note")
        updated = sum(1 for a in actions if a.kind == "update_note")
        closed = sum(1 for a in actions if a.kind == "close_note")
        if dry_run:
            return SyncSummary(planned=len(actions), applied=0, created=created, updated=updated, closed=closed)

        applied = 0
        for action in actions:
            if action.kind == "create_note":
                self.client.create_mr_note(pr_id, action.payload["body"])
            else:
                self.client.update_mr_note(pr_id, action.payload["note_id"], action.payload["body"])
            applied += 1

        summary = build_summary_note(created=created, updated=updated, closed=closed, total_findings=created + updated)
        old = find_existing_summary_note(self.client.get_mr_notes(pr_id))
        if old:
            self.client.update_mr_note(pr_id, old["id"], summary)
        else:
            self.client.create_mr_note(pr_id, summary)

        return SyncSummary(planned=len(actions), applied=applied, created=created, updated=updated, closed=closed)
