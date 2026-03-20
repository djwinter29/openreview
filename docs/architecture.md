# Architecture

This document describes the current runtime structure of `openreview` after the package refactor to a layered layout.

## Design Goals

- keep the CLI thin
- keep runtime wiring in an outer composition layer
- isolate business logic from provider-specific APIs
- make SCM and model integrations replaceable
- support additional review agents without rewriting orchestration

## Current Architecture Decisions

The following decisions are now the intended direction for the next phase of the design:

- SCM providers should converge on one typed review-state model at the port boundary
- sync planning should use typed provider-neutral action models across the SCM boundary
- provider-specific flexibility should remain in translation and transport details, not in the core SCM contracts
- reviewers should depend on an injected review-focused model gateway rather than raw model transport requests
- SCM configuration should use provider-specific typed config models instead of a shared nullable option bag
- the reviewer layer should stay intentionally simple until there is a second real reviewer with distinct behavior and configuration needs

These decisions are meant to keep the current architecture moving toward stronger contracts without introducing speculative abstractions too early.

## Package Layout

- `src/openreview/application/`
  - CLI-facing commands and orchestration helpers
  - coordinates workflows such as `run` and `sync`
- `src/openreview/bootstrap.py`
  - outer composition layer for provider selection, model gateway wiring, and assembly of SCM services through a provider registry
- `src/openreview/domain/`
  - core entities such as findings and diff hunks
  - provider-neutral business rules for filtering, fingerprinting, mapping, and sync planning
- `src/openreview/ports/`
  - stable interfaces for SCM providers and model adapters
- `src/openreview/reviewers/`
  - built-in reviewer implementations plus a registry of reviewer registrations consumed by routing
- `src/openreview/adapters/`
  - concrete integrations for SCM systems and model providers
- `src/openreview/config/`
  - configuration loading and schema validation

## Runtime Flow

### `openreview run`

The `run` command performs the full workflow:

1. load `.openreview.yml`
2. resolve provider-specific SCM config and model credentials
3. determine changed files
4. ask the configured reviewer to inspect those files
5. map findings back to changed hunks
6. filter, deduplicate, and cap findings
7. plan provider-neutral lifecycle actions against normalized existing comments
8. apply or print the resulting actions

Provider behavior differs slightly by platform:

- Azure DevOps reads changed files from the latest pull request iteration
- GitHub and GitLab currently use local git diff information for changed file discovery

### `openreview sync`

The `sync` command skips AI review and starts from a prepared findings JSON file:

1. parse and validate the JSON payload
2. resolve provider-specific SCM config
3. plan provider-neutral lifecycle actions
4. apply or print those actions

## Key Domain Concepts

### Review finding

A finding is the normalized unit of review output. Each finding includes:

- path
- line
- severity
- message
- fingerprint
- confidence
- optional suggestion and metadata

### Fingerprint

Fingerprints are used to reconnect newly generated findings to previously posted review comments. The current implementation intentionally ignores line number when building the fingerprint so a finding can survive line movement when the message is effectively unchanged.

### Sync action

Sync planning now converts desired findings and normalized existing comments into typed provider-neutral actions first. Creation actions encode capability explicitly: inline-comment creation is distinct from general note creation. SCM adapters then translate those neutral actions into Azure DevOps threads, GitHub review comments, or GitLab notes.

The neutral planner currently covers lifecycle decisions such as:

- create comment or thread
- reopen a closed discussion
- append an updated comment
- close resolved feedback

This split keeps lifecycle rules in one place while letting each provider keep only normalization and transport-specific API mapping.

### Composition layer

The outer composition layer resolves provider-specific SCM config from environment-backed inputs, uses a single SCM provider registry to assemble the provider plus changed-path collector pair, and injects a configured review-focused model gateway used by reviewers. Application services receive these dependencies explicitly and do not instantiate concrete adapters.

### Review model gateway

Reviewers do not build raw model requests or branch on provider-specific model behavior. They receive a configured gateway that accepts a typed review request and returns structured review findings. Prompt construction, response-schema wording, provider selection, API keys, model names, base URLs, JSON parsing, and response normalization stay outside the reviewer layer. Malformed model output is treated as a contract failure, not as an empty finding set, so the application layer can fail fast or choose an explicit degradation policy. The model error taxonomy also lives at the port boundary, which keeps application code dependent on `ports/model.py` rather than on adapter-defined exception types.

## Extension Points

- add new SCM providers by implementing the SCM port and registering one SCM composition entry
- add new review agents under `reviewers/agents/`
- add new reviewer registrations by pairing metadata and factory in one registry entry
- add new model providers under `adapters/model/`
- expand routing logic in `reviewers/router.py` when multiple agents become active

## Near-Term Direction

### SCM boundary

The near-term goal is to keep converging all SCM providers on a single typed review-state model and stronger typed action contracts at the port boundary. Provider-specific API payloads should remain isolated inside adapter translation layers.

### Reviewer subsystem

The reviewer subsystem should remain deliberately simple until a second real reviewer exists. That means the current registry and routing structure should support one built-in reviewer cleanly, but it should avoid speculative complexity until multi-reviewer execution is a concrete product need.

## Test Layout

Tests are organized to mirror the production package structure wherever practical:

- root package tests for package-level modules such as `cli.py`
- `application/services/` tests for orchestration helpers
- `domain/services/` tests for business rules
- `adapters/scm/` tests for provider clients, sync logic, and exports

That keeps source-to-test mapping explicit and makes stale tests easier to spot during refactors.