from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InlineCommentTarget:
    path: str
    line: int


@dataclass(frozen=True)
class CreateFindingComment:
    fingerprint: str
    body: str
    target: InlineCommentTarget | None = None


@dataclass(frozen=True)
class RefreshFindingComment:
    fingerprint: str
    comment_id: int | str
    body: str
    reopen: bool = False


@dataclass(frozen=True)
class CloseFindingComment:
    fingerprint: str
    comment_id: int | str
    body: str


SyncAction = CreateFindingComment | RefreshFindingComment | CloseFindingComment


def sync_action_kind(action: SyncAction) -> str:
    if isinstance(action, CreateFindingComment):
        return "create"
    if isinstance(action, RefreshFindingComment):
        return "refresh"
    if isinstance(action, CloseFindingComment):
        return "close"
    raise TypeError(f"unsupported sync action: {type(action)!r}")