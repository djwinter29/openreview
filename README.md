# openreview

AI-assisted PR review automation focused on Azure DevOps, with GitHub provider support in progress.

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

## Configuration

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
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, default in CLI)

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

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e . pytest pytest-cov build twine
pytest -q
pytest --cov=src/openreview --cov-report=term -q
```

## License

MIT
