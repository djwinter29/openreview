from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Hunk:
    path: str
    start: int
    end: int


def changed_hunks(repo_root: Path, target_ref: str) -> dict[str, list[Hunk]]:
    cmd = [
        "git",
        "-C",
        str(repo_root),
        "diff",
        "--unified=0",
        f"{target_ref}...HEAD",
    ]
    out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL)

    file_hunks: dict[str, list[Hunk]] = {}
    cur_path: str | None = None
    hunk_re = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")

    for line in out.splitlines():
        if line.startswith("+++ b/"):
            cur_path = "/" + line[len("+++ b/") :]
            file_hunks.setdefault(cur_path, [])
            continue
        m = hunk_re.match(line)
        if m and cur_path:
            start = int(m.group(1))
            count = int(m.group(2) or "1")
            end = start + max(count - 1, 0)
            file_hunks[cur_path].append(Hunk(path=cur_path, start=start, end=end))

    return file_hunks


def nearest_line_or_none(path: str, line: int, hunks_by_file: dict[str, list[Hunk]]) -> int | None:
    hunks = hunks_by_file.get(path) or []
    if not hunks:
        return None

    for h in hunks:
        if h.start <= line <= h.end:
            return line

    # snap to nearest changed hunk start
    nearest = min(hunks, key=lambda h: min(abs(line - h.start), abs(line - h.end)))
    return nearest.start
