from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InlineCommentTarget:
    path: str
    line: int


@dataclass(frozen=True)
class CreateInlineFindingComment:
    fingerprint: str
    body: str
    target: InlineCommentTarget


@dataclass(frozen=True)
class CreateGeneralFindingComment:
    fingerprint: str
    body: str


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


SyncAction = CreateInlineFindingComment | CreateGeneralFindingComment | RefreshFindingComment | CloseFindingComment


def sync_action_kind(action: SyncAction) -> str:
    if isinstance(action, (CreateInlineFindingComment, CreateGeneralFindingComment)):
        return "create"
    if isinstance(action, RefreshFindingComment):
        return "refresh"
    if isinstance(action, CloseFindingComment):
        return "close"
    raise TypeError(f"unsupported sync action: {type(action)!r}")