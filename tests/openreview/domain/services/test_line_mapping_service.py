import subprocess
from pathlib import Path

from openreview.domain.services.line_mapping_service import changed_hunks, nearest_line_or_none


def sh(cmd, cwd: Path):
    subprocess.check_call(cmd, cwd=cwd)


def test_changed_hunks_and_nearest(tmp_path: Path) -> None:
    sh(["git", "init"], tmp_path)
    sh(["git", "config", "user.email", "a@b.com"], tmp_path)
    sh(["git", "config", "user.name", "t"], tmp_path)

    test_file = tmp_path / "a.c"
    test_file.write_text("line1\nline2\nline3\n")
    sh(["git", "add", "."], tmp_path)
    sh(["git", "commit", "-m", "init"], tmp_path)

    sh(["git", "branch", "-M", "main"], tmp_path)
    sh(["git", "branch", "origin/main"], tmp_path)

    sh(["git", "checkout", "-b", "feature/test"], tmp_path)
    test_file.write_text("line1\nline2 changed\nline3\nline4\n")
    sh(["git", "add", "."], tmp_path)
    sh(["git", "commit", "-m", "change"], tmp_path)

    hunks = changed_hunks(tmp_path, "origin/main")
    assert "/a.c" in hunks
    assert nearest_line_or_none("/a.c", 2, hunks) is not None
    assert nearest_line_or_none("/a.c", 200, hunks) is None
    assert nearest_line_or_none("/missing.c", 1, hunks) is None
