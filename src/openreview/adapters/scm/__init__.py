"""SCM adapters for GitHub, GitLab, and Azure DevOps."""

from openreview.adapters.scm.factory import make_azure, make_github, make_gitlab
from openreview.adapters.scm.runtime import AzureChangedPathCollector, GitDiffChangedPathCollector, ProviderSyncExecutor, run_sync_pipeline
from openreview.ports.scm import ProviderOptions, SyncExecutionError

__all__ = [
	"ProviderOptions",
	"SyncExecutionError",
	"run_sync_pipeline",
	"AzureChangedPathCollector",
	"GitDiffChangedPathCollector",
	"ProviderSyncExecutor",
	"make_azure",
	"make_github",
	"make_gitlab",
]
