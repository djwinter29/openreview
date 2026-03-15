# openreview

AI-assisted PR review automation for Azure DevOps, GitHub, and GitLab, with pluggable AI model providers.

## Documentation

Project documentation now lives in the docs folder.

- Overview: [docs/README.md](docs/README.md)
- Architecture: [docs/architecture.md](docs/architecture.md)
- Configuration and CLI usage: [docs/configuration.md](docs/configuration.md)
- CI and pipeline notes: [docs/ci.md](docs/ci.md)

The Azure DevOps sample pipeline file is now located at `.azuredevops/azure-pipelines.yml`.

## What it does (current)
- Runs on PR updates (new push/force-push)
- Reviews changed code with AI
- Tracks findings using stable fingerprints
- Syncs review lifecycle automatically:
  - create new review comment
  - update/re-comment when finding changes
  - close when resolved
  - reopen when issue returns

## Install

From source:

```bash
pip install -e .
```

From GitHub main (recommended during active development):

```bash
pip install "git+https://github.com/djwinter29/openreview.git@main"
```

After stable release:

```bash
pip install openreview
```

## CLI

```bash
openreview version
openreview plan
```

### 1) Sync from prepared findings JSON

Azure (default):

```bash
openreview sync \
  --pr-id 123 \
  --findings-file findings.json \
  --provider azure \
  --dry-run
```

GitHub:

```bash
openreview sync \
  --pr-id 123 \
  --findings-file findings.json \
  --provider github \
  --dry-run
```

### 2) Full run (diff -> AI review -> sync)

Azure:

```bash
openreview run \
  --pr-id 123 \
  --repo-root . \
  --provider azure \
  --dry-run
```

GitHub (MVP mode uses local git diff):

```bash
openreview run \
  --pr-id 123 \
  --repo-root . \
  --provider github \
  --base-ref origin/main \
  --dry-run
```

Without `--dry-run`, comments are applied.

### Summary output

Both `sync` and `run` print a summary at the end. For machine-readable output, use `--summary-json`.

```bash
openreview sync \
  --pr-id 123 \
  --findings-file findings.json \
  --provider github \
  --dry-run \
  --summary-json
```

Example JSON fields:
- `findings_raw` / `findings_filtered` (when available)
- `planned_actions`
- `applied_actions`
- `created`, `updated`, `closed`, `skipped`

## Configuration

See [docs/configuration.md](docs/configuration.md) for command flow, provider setup, environment variables, and `.openreview.yml` rules.

You can pass options explicitly, or use env vars:

### Azure DevOps
- `AZDO_ORG`
- `AZDO_PROJECT`
- `AZDO_REPO_ID`
- `AZDO_PAT`

### GitHub
- `GITHUB_OWNER`
- `GITHUB_REPO`
- `GITHUB_TOKEN`

### GitLab
- `GITLAB_PROJECT_ID`
- `GITLAB_TOKEN`
- `GITLAB_BASE_URL` (optional, default: `https://gitlab.com/api/v4`)

### AI
- OpenAI:
  - `OPENAI_API_KEY`
- Claude (Anthropic):
  - `ANTHROPIC_API_KEY`
- DeepSeek:
  - `DEEPSEEK_API_KEY`

CLI model options:
- `--ai-provider openai|claude|deepseek`
- `--ai-model <model-name>` (default: `gpt-4.1-mini`)
- `--ai-api-key <key>` (optional explicit override)
- `--ai-base-url <url>` (optional)
- `--openai-api-key <key>` (legacy compatibility option)

## `.openreview.yml` rules

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

## Findings JSON format

`openreview sync` validates findings input and reports clear CLI errors for malformed payloads (missing required fields, invalid severity, invalid line/confidence types).


`findings.json` is an array:

```json
[
  {
    "path": "/src/foo.c",
    "line": 42,
    "severity": "warning",
    "message": "Potential null dereference",
    "fingerprint": "foo-null"
  }
]
```

## CI quality gate

CI runs tests with coverage and enforces a minimum threshold:

```bash
pytest --cov=src/openreview --cov-report=term --cov-fail-under=75
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e . pytest pytest-cov build twine
pytest -q
pytest --cov=src/openreview --cov-report=term -q
```

## Repository Layout

- `src/openreview/`: application, domain, reviewer, adapter, and config code
- `tests/openreview/`: unit test suite aligned to the runtime architecture
- `docs/`: project documentation and operational notes
- `.azuredevops/azure-pipelines.yml`: sample Azure DevOps pipeline

## License

MIT
