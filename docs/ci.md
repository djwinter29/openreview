# CI And Pipelines

This project currently ships documentation and sample automation for both GitHub Actions and Azure DevOps.

## GitHub Actions

The GitHub workflow lives at `.github/workflows/ci.yml`.

It currently:

- runs the test suite
- enforces coverage requirements
- generates Doxygen HTML documentation
- generates LaTeX output and builds `refman.pdf`
- uploads HTML and PDF artifacts

## Azure DevOps

The Azure DevOps sample pipeline lives at `.azuredevops/azure-pipelines.yml`.

This file is intended as a starting point for Azure DevOps repositories that want to run `openreview` against pull requests and publish generated documentation artifacts.

The sample pipeline currently:

- installs Python 3.11
- installs `openreview`
- runs `openreview run`
- installs Doxygen, Graphviz, and LaTeX tooling
- generates HTML and LaTeX documentation
- builds `refman.pdf`
- publishes HTML and PDF artifacts

## Doxygen Inputs

The Doxygen configuration includes:

- `README.md`
- `docs/`
- `src/openreview/`

That keeps user-facing Markdown and API-oriented Python documentation in the same published doc set.
