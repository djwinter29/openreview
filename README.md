# openreview

AI-assisted PR review automation focused on Azure DevOps.

## What it does (MVP)
- Triggers on PR updates (new push/force-push)
- Reads existing Azure DevOps PR review threads
- Compares findings by stable `fingerprint`
- Syncs review state automatically:
  - create new thread for new finding
  - append comment when finding text/location changed
  - close thread when finding is gone
  - reopen thread if finding comes back

## Install

From source:

```bash
pip install -e .
```

After publish:

```bash
pip install openreview
```

## CLI

```bash
openreview version
openreview plan
```

### Mode A: sync from prepared findings JSON

```bash
openreview sync \
  --pr-id 123 \
  --findings-file findings.json \
  --dry-run
```

Without `--dry-run`, actions are applied to Azure DevOps.

### Mode B: full pipeline run (diff -> AI review -> sync)

```bash
openreview run \
  --pr-id 123 \
  --repo-root . \
  --dry-run
```

Without `--dry-run`, this command posts/updates/closes PR comments automatically.

## Azure DevOps configuration

You can pass options explicitly, or use env vars:

- `AZDO_ORG`
- `AZDO_PROJECT`
- `AZDO_REPO_ID`
- `AZDO_PAT`
- `OPENAI_API_KEY`
- `OPENAI_MODEL` (optional, default in CLI)

Example:

```bash
export AZDO_ORG=my-org
export AZDO_PROJECT=my-project
export AZDO_REPO_ID=12345678-aaaa-bbbb-cccc-1234567890ab
export AZDO_PAT=***

openreview run --pr-id 123 --repo-root .
```

## Findings JSON format

`findings.json` must be an array of objects:

```json
[
  {
    "path": "/src/foo.c",
    "line": 42,
    "severity": "warning",
    "message": "Potential null dereference",
    "fingerprint": "foo-null-42"
  }
]
```

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -U pip
pip install -e . pytest build twine
pytest
python -m build
python -m twine check dist/*
```

## License

MIT
