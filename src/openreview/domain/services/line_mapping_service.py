"""! Services for mapping findings to changed diff hunks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from openreview.domain.entities.diff_hunk import Hunk


def changed_hunks(repo_root: Path, target_ref: str) -> dict[str, list[Hunk]]:
    """! Parse zero-context git diff output into hunks keyed by file path."""

    cmd = ["git", "-C", str(repo_root), "diff", "--unified=0", f"{target_ref}...HEAD"]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)

    file_hunks: dict[str, list[Hunk]] = {}
    cur_path: str | None = None
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    for line in out.splitlines():
        if line.startswith("+++ b/"):
            cur_path = "/" + line[len("+++ b/") :]
            file_hunks.setdefault(cur_path, [])
            continue
        match = hunk_re.match(line)
        if match and cur_path:
            start = int(match.group(1))
            count = int(match.group(2) or "1")
            end = start + max(count - 1, 0)
            file_hunks[cur_path].append(Hunk(path=cur_path, start=start, end=end))

    return file_hunks


def nearest_line_or_none(path: str, line: int, hunks_by_file: dict[str, list[Hunk]]) -> int | None:
    """! Return the line when it falls inside a changed hunk, otherwise `None`."""

    hunks = hunks_by_file.get(path) or []
    if not hunks:
        return None

    for hunk in hunks:
        if hunk.start <= line <= hunk.end:
            return line

    return None
