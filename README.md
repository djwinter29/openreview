# openreview

AI-assisted PR review automation focused on Azure DevOps.

## Goals
- Trigger on PR updates (new push/force-push)
- Re-run review with LLM policy
- Update existing review comments when code context changes
- Auto-resolve stale comments; create new comments for new findings

## Status
Early scaffold (MVP in progress).

## Planned MVP
1. Fetch PR threads/comments from Azure DevOps
2. Compute mapping from previous findings to current diff hunks
3. Upsert review comments (new/update/resolve)
4. Run in CI via GitHub Actions

## Install (dev)
```bash
pip install -e .
openreview --help
```
