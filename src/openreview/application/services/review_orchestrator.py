"""! Application orchestration for the end-to-end review workflow."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

import typer
from rich import print

from openreview.config import OpenReviewConfig
from openreview.domain.entities.changed_file import ChangedFile
from openreview.domain.entities.finding import ReviewFinding
from openreview.domain.services.finding_filter_service import (
	apply_hunk_mapping,
	cap_per_file,
	filter_findings,
	path_allowed,
)
from openreview.domain.services.line_mapping_service import changed_hunks
from openreview.ports.model import ReviewModelGateway
from openreview.ports.scm import ChangedPathCollector
from openreview.reviewers.router import choose_reviewers


@dataclass(frozen=True)
class ReviewExecutionResult:
	"""! Output of the review generation stage before sync is applied."""

	findings: list[ReviewFinding]
	raw_findings: int


def execute_review(
	*,
	pr_id: int,
	repo_root: Path,
	base_ref: str,
	config: OpenReviewConfig,
	changed_path_collector: ChangedPathCollector,
	review_model: ReviewModelGateway,
	max_files: int,
	reviewer_strategy: str = "fixed",
) -> ReviewExecutionResult:
	"""! Execute changed-file discovery, reviewer invocation, and finding filtering."""

	try:
		changed_paths = changed_path_collector.collect_changed_paths(pr_id, repo_root, base_ref)
	except subprocess.CalledProcessError as err:
		output = (err.output or "").strip()
		msg = f"Unable to diff against base ref '{base_ref}'."
		if output:
			msg = f"{msg} git said: {output}"
		raise typer.BadParameter(msg) from err

	changed_paths = [
		path for path in changed_paths if path_allowed(path, config.rules.include_paths, config.rules.exclude_paths)
	]
	try:
		hunks = changed_hunks(repo_root, base_ref)
	except subprocess.CalledProcessError as err:
		raise typer.BadParameter(f"Unable to map changed hunks against '{base_ref}'.") from err

	files = [ChangedFile(path=path, hunks=hunks.get(path, [])) for path in changed_paths[:max_files]]
	print(f"Changed files considered: {len(files)}")

	findings: list[ReviewFinding] = []
	for reviewer in choose_reviewers(reviewer_strategy):
		findings.extend(
			reviewer.review_files(
				review_model=review_model,
				files=files,
				repo_root=repo_root,
			)
		)

	raw_findings = len(findings)
	print(f"AI findings (raw): {raw_findings}")

	findings = apply_hunk_mapping(findings, hunks, config.rules.changed_lines_only)
	findings = filter_findings(findings, config.rules.min_severity, config.rules.min_confidence)
	findings = cap_per_file(findings, config.rules.max_comments_per_file)
	findings = findings[: config.rules.max_comments]
	print(f"AI findings (filtered): {len(findings)}")
	return ReviewExecutionResult(findings=findings, raw_findings=raw_findings)
