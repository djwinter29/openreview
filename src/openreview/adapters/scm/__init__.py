"""SCM adapters for GitHub, GitLab, and Azure DevOps."""

from openreview.adapters.scm.composition import ScmServices, compose_scm_services
from openreview.adapters.scm.factory import make_azure, make_github, make_gitlab
from openreview.adapters.scm.runtime import AzureChangedPathCollector, GitDiffChangedPathCollector, ProviderSyncExecutor, run_sync_pipeline
from openreview.ports.scm import AzureDevOpsScmConfig, GitHubScmConfig, GitLabScmConfig, ScmConfig, SyncExecutionError

__all__ = [
	"AzureDevOpsScmConfig",
	"GitHubScmConfig",
	"GitLabScmConfig",
	"ScmConfig",
	"ScmServices",
	"SyncExecutionError",
	"compose_scm_services",
	"run_sync_pipeline",
	"AzureChangedPathCollector",
	"GitDiffChangedPathCollector",
	"ProviderSyncExecutor",
	"make_azure",
	"make_github",
	"make_gitlab",
]
