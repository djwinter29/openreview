import pytest

from openreview.adapters.scm.runtime import ProviderSyncExecutor, run_sync_pipeline
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.entities.sync_action import CreateGeneralFindingComment
from openreview.ports.scm import ExistingReviewComment, SyncExecutionError, SyncSummary


class DummyProvider:
    def __init__(self) -> None:
        self.list_calls: list[int] = []
        self.apply_calls: list[tuple[int, list[CreateGeneralFindingComment], bool]] = []

    def list_existing(self, pr_id: int) -> list[ExistingReviewComment]:
        self.list_calls.append(pr_id)
        return [ExistingReviewComment(comment_id=1, fingerprint="old", body="body")]

    def apply(self, pr_id: int, actions, *, dry_run: bool = False) -> SyncSummary:
        self.apply_calls.append((pr_id, actions, dry_run))
        return SyncSummary(planned=len(actions), applied=len(actions), created=1, updated=0, closed=0)


def test_run_sync_pipeline_uses_injected_planner_outside_provider() -> None:
    provider = DummyProvider()
    finding = ReviewFinding(path="/a.py", line=3, severity="warning", message="m", fingerprint="fp-1")

    def planner(findings, existing):
        assert findings == [finding]
        assert existing[0].fingerprint == "old"
        return [CreateGeneralFindingComment(fingerprint="fp-1", body="planned")]

    actions, summary = run_sync_pipeline(provider, 42, [finding], planner=planner, dry_run=True)

    assert provider.list_calls == [42]
    assert provider.apply_calls[0][0] == 42
    assert provider.apply_calls[0][2] is True
    assert len(actions) == 1
    assert summary.applied == 1


def test_provider_sync_executor_wraps_planner_failures_as_plan_errors() -> None:
    provider = DummyProvider()
    executor = ProviderSyncExecutor(provider, planner=lambda findings, existing: (_ for _ in ()).throw(RuntimeError("boom")))

    with pytest.raises(SyncExecutionError) as exc:
        executor.sync(1, [], dry_run=True)

    assert exc.value.step == "plan"