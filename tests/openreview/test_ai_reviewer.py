from pathlib import Path

from openreview import ai_reviewer
from openreview.ai_reviewer import _fp


def test_fingerprint_stable() -> None:
    a = _fp('/a.c', 12, 'Null pointer risk')
    b = _fp('/a.c', 12, 'null pointer risk')
    assert a == b


def test_normalize_message_and_fp_stability() -> None:
    a = ai_reviewer._fp('/a.c', 10, 'Null pointer at line 10')
    b = ai_reviewer._fp('/a.c', 999, ' null   pointer at line 999 ')
    assert a == b


def test_review_changed_files_parses_items(tmp_path: Path, monkeypatch) -> None:
    f = tmp_path / 'a.c'
    f.write_text('int main(){return 0;}')

    def fake_call(api_key: str, model: str, prompt: str):
        return [
            {
                'line': 3,
                'severity': 'ERROR',
                'confidence': 0.91,
                'message': 'Potential null dereference',
                'suggestion': 'Add a null check.'
            },
            {
                'line': 'x',
                'severity': 'weird',
                'confidence': 'bad',
                'message': ' style issue ',
                'suggestion': ''
            },
        ]

    monkeypatch.setattr(ai_reviewer, '_call_openai_json', fake_call)

    findings = ai_reviewer.review_changed_files(
        api_key='k',
        model='m',
        files=[ai_reviewer.ChangedFile(path='/a.c')],
        repo_root=tmp_path,
    )

    assert len(findings) == 2
    assert findings[0].severity == 'error'
    assert findings[0].confidence == 0.91
    assert findings[0].line == 3
    assert findings[1].severity == 'warning'
    assert findings[1].confidence == 0.7
    assert findings[1].line == 1


def test_review_changed_files_skips_missing_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(ai_reviewer, '_call_openai_json', lambda *args, **kwargs: [])
    findings = ai_reviewer.review_changed_files(
        api_key='k',
        model='m',
        files=[ai_reviewer.ChangedFile(path='/missing.c')],
        repo_root=tmp_path,
    )
    assert findings == []
