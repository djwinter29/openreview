from pathlib import Path

from openreview.config import load_config


def test_load_default_when_missing(tmp_path: Path) -> None:
    cfg = load_config(tmp_path / '.openreview.yml')
    assert cfg.rules.min_confidence > 0


def test_load_config_file(tmp_path: Path) -> None:
    p = tmp_path / '.openreview.yml'
    p.write_text('rules:\n  min_confidence: 0.8\n  max_comments_per_file: 2\n')
    cfg = load_config(p)
    assert cfg.rules.min_confidence == 0.8
    assert cfg.rules.max_comments_per_file == 2
