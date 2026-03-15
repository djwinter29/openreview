# Configuration And CLI Usage

This document summarizes how to run `openreview`, how provider credentials are resolved, and how policy settings affect the generated review output.

## Commands

## `openreview version`

Prints the installed package version.

## `openreview plan`

Prints the current high-level workflow summary.

## `openreview sync`

Use this command when another system already produced the findings JSON.

Example:

```bash
openreview sync \
  --pr-id 123 \
  --findings-file findings.json \
  --provider github \
  --dry-run
```

What it does:

- validates the JSON payload
- resolves provider credentials
- plans comment updates against the existing review state
- optionally applies those changes

## `openreview run`

Use this command for the full review loop.

Example:

```bash
openreview run \
  --pr-id 123 \
  --repo-root . \
  --provider azure \
  --ai-provider openai \
  --ai-model gpt-4.1-mini \
  --dry-run
```

What it does:

- discovers changed files
- invokes the active review agent
- filters and maps findings
- synchronizes the resulting comments back to the provider

## Provider Resolution

SCM provider selection is controlled by `--provider`.

Supported values:

- `azure`
- `github`
- `gitlab`

The application accepts explicit CLI options first and then falls back to environment variables.

### Azure DevOps

Required values:

- `AZDO_ORG`
- `AZDO_PROJECT`
- `AZDO_REPO_ID`
- `AZDO_PAT`

Matching CLI options:

- `--organization`
- `--project`
- `--repository-id`
- `--pat`

### GitHub

Required values:

- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_TOKEN`

Matching CLI options:

- `--github-owner`
- `--github-repo`
- `--github-token`

### GitLab

Required values:

- `GITLAB_PROJECT_ID`
- `GITLAB_TOKEN`

Optional value:

- `GITLAB_BASE_URL`

Matching CLI options:

- `--gitlab-project-id`
- `--gitlab-token`
- `--gitlab-base-url`

## Model Provider Resolution

Supported model providers:

- `openai`
- `claude`
- `deepseek`

Common CLI options:

- `--ai-provider`
- `--ai-model`
- `--ai-api-key`
- `--ai-base-url`

Environment variable fallback:

- OpenAI: `OPENAI_API_KEY`
- Claude: `ANTHROPIC_API_KEY`
- DeepSeek: `DEEPSEEK_API_KEY`

The legacy `--openai-api-key` option is still accepted for OpenAI compatibility.

## `.openreview.yml`

The configuration file is optional. When it is missing, defaults from the schema are used.

Example:

```yaml
rules:
  min_confidence: 0.65
  min_severity: warning
  max_comments: 25
  max_comments_per_file: 3
  include_paths: []
  exclude_paths:
    - /tests/
    - /docs/
  changed_lines_only: true
```

### Rule Meanings

- `min_confidence`: drops findings below the threshold
- `min_severity`: keeps only findings at or above the selected severity
- `max_comments`: global cap after filtering
- `max_comments_per_file`: per-file cap after ranking by severity and confidence
- `include_paths`: optional allow-list prefixes
- `exclude_paths`: deny-list prefixes
- `changed_lines_only`: when true, keep only findings that map to changed hunks

## Findings JSON

`openreview sync` expects a JSON array of finding objects.

Minimum shape:

```json
[
  {
    "path": "/src/foo.py",
    "line": 42,
    "severity": "warning",
    "message": "Potential issue",
    "fingerprint": "abc123"
  }
]
```

Validation rules include:

- payload must be a JSON array
- each item must be an object
- `line` must be an integer greater than or equal to 1
- `severity` must be `info`, `warning`, or `error`
- `confidence`, when provided, must be in the range `[0,1]`

## Summary Output

Both `run` and `sync` print a summary when execution completes.

Use `--summary-json` for machine-readable output.

Current fields include:

- `findings_raw`
- `findings_filtered`
- `planned_actions`
- `applied_actions`
- `created`
- `updated`
- `closed`
- `skipped`