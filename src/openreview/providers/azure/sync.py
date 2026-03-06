from __future__ import annotations

from openreview.sync_core import (
    build_summary_content,
    find_summary_thread,
    plan_sync,
)


# Azure currently reuses the generic thread-sync engine.
# Keep Azure-facing names here so provider modules stay layout-consistent
# with GitHub/GitLab (`providers/*/sync.py`).
plan_azure_sync = plan_sync
build_azure_summary = build_summary_content
find_azure_summary_thread = find_summary_thread
