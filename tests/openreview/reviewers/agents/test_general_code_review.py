from pathlib import Path
from types import SimpleNamespace

from openreview.domain.services.fingerprint_service import build_fingerprint as _fp
from openreview.reviewers.agents import general_code_review as ai_reviewer


class DummyModelGateway:
    def __init__(self, text: str = "[]"):
        self.text = text

    def generate(self, request):
        return SimpleNamespace(text=self.text)


def test_fingerprint_stable() -> None:
    assert _fp("/a.c", 12, "Null pointer risk") == _fp("/a.c", 12, "null pointer risk")


def test_normalize_message_and_fp_stability() -> None:
    assert _fp("/a.c", 10, "Null pointer at line 10") == _fp("/a.c", 999, " null   pointer at line 999 ")


def test_review_changed_files_parses_items(tmp_path: Path, monkeypatch) -> None:
    test_file = tmp_path / "a.c"
    test_file.write_text("int main(){return 0;}")

    def fake_call(model_gateway, api_key: str, model: str, prompt: str):
        return [
            {
                "line": 3,
                "severity": "ERROR",
                "confidence": 0.91,
                "message": "Potential null dereference",
                "suggestion": "Add a null check.",
            },
            {
                "line": "x",
                "severity": "weird",
                "confidence": "bad",
                "message": " style issue ",
                "suggestion": "",
            },
        ]

    monkeypatch.setattr(ai_reviewer, "_call_openai_json", fake_call)

    findings = ai_reviewer.review_changed_files(
        model_gateway=DummyModelGateway(),
        api_key="k",
        model="m",
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


def test_review_changed_files_skips_missing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ai_reviewer, "_call_openai_json", lambda *args, **kwargs: [])
    findings = ai_reviewer.review_changed_files(
        model_gateway=DummyModelGateway(),
        api_key="k",
        model="m",
        files=[ai_reviewer.ChangedFile(path="/missing.c")],
        repo_root=tmp_path,
    )
    assert findings == []
