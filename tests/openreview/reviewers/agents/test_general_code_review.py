from pathlib import Path

from openreview.domain.entities.diff_hunk import Hunk
from openreview.domain.entities.finding import ReviewFinding
from openreview.ports.model import ReviewRequest, StructuredReviewFinding
from openreview.domain.services.fingerprint_service import build_fingerprint as _fp
from openreview.reviewers.agents import general_code_review as ai_reviewer


class DummyReviewModel:
    def __init__(self, findings: list[StructuredReviewFinding] | None = None):
        self.findings = findings or []
        self.requests: list[ReviewRequest] = []

    def review(self, request: ReviewRequest) -> list[StructuredReviewFinding]:
        self.requests.append(request)
        return list(self.findings)


def test_fingerprint_stable() -> None:
    assert _fp("/a.c", 12, "Null pointer risk") == _fp("/a.c", 12, "null pointer risk")


def test_normalize_message_and_fp_stability() -> None:
    assert _fp("/a.c", 10, "Null pointer at line 10") == _fp("/a.c", 999, " null   pointer at line 999 ")


def test_review_changed_files_parses_items(tmp_path: Path, monkeypatch) -> None:
    test_file = tmp_path / "a.c"
    test_file.write_text("int main(){return 0;}")
    review_model = DummyReviewModel(
        [
            StructuredReviewFinding(
                line=3,
                severity="error",
                confidence=0.91,
                message="Potential null dereference",
                suggestion="Add a null check.",
            ),
            StructuredReviewFinding(
                line=1,
                severity="warning",
                confidence=0.7,
                message=" style issue ",
                suggestion="",
            ),
        ]
    )

    findings = ai_reviewer.review_changed_files(
        review_model=review_model,
        files=[ai_reviewer.ChangedFile(path="/a.c")],
        repo_root=tmp_path,
    )

    assert len(findings) == 2
    assert findings[0].severity == "error"
    assert findings[0].confidence == 0.91
    assert findings[0].line == 3
    assert findings[1].severity == "warning"
    assert findings[1].confidence == 0.7
    assert findings[1].line == 1
    assert len(review_model.requests) == 1
    assert review_model.requests[0].path == "/a.c"
    assert review_model.requests[0].content == "int main(){return 0;}"
    assert review_model.requests[0].instructions == "Find practical issues in changed code only."


def test_review_changed_files_skips_missing_file(tmp_path: Path, monkeypatch) -> None:
    del monkeypatch
    findings = ai_reviewer.review_changed_files(
        review_model=DummyReviewModel(),
        files=[ai_reviewer.ChangedFile(path="/missing.c")],
        repo_root=tmp_path,
    )
    assert findings == []


def test_review_changed_files_prioritizes_changed_hunks_over_file_prefix(tmp_path: Path) -> None:
    test_file = tmp_path / "a.c"
    lines = [f"line {i}" for i in range(1, 61)]
    lines[49] = "important changed line"
    test_file.write_text("\n".join(lines), encoding="utf-8")
    review_model = DummyReviewModel()

    ai_reviewer.review_changed_files(
        review_model=review_model,
        files=[ai_reviewer.ChangedFile(path="/a.c", hunks=[Hunk(path="/a.c", start=50, end=50)])],
        repo_root=tmp_path,
        max_file_chars=120,
    )

    assert len(review_model.requests) == 1
    assert "Changed excerpt (48-52)" in review_model.requests[0].content
    assert "50: important changed line" in review_model.requests[0].content
    assert "1: line 1" not in review_model.requests[0].content
