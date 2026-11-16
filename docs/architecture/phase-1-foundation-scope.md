# BharatCrop Intelligence: Phase 1 Foundation Scope

**Status:** Proposed scope for human approval; no Phase 1 implementation is authorized by this document. This scope narrows Phase 1 to a reversible tooling foundation. It does not satisfy the broader future Phase 1 acceptance criteria in `phase-acceptance-criteria.md`, which include database, authentication, deployment, and other work explicitly excluded here.

## 1. Purpose and evidence baseline

The repository audit records 22 numbered notebooks and substantial data, metadata, model, and report assets, but no application source, dependency manifests, test suite, CI workflow, database schema/migrations, or deployment stack. The present repository contains the Phase 0 documentation created after the audit; the audit's no-`docs/` statement is historical. The current top-level IntelliJ configuration is not evidence that Java is the target application stack.

This proposal permits only repository/tooling work, formatting and automated quality checks for new application-owned files, minimal provider-independent scaffolding, and checks that protect the research/documentation baseline. Existing research assets and Phase 0 documents remain out of scope for modification.

## 2. Exact permitted work

All paths written as `<approved-app-root>` or `<approved-tooling-path>` below are placeholders, not existing paths. They must be selected and approved before work begins. Proposed commands are templates, not commands verified to exist in this repository. Replace them only after the package managers, tool versions, and CI environment are approved.

| Permitted change | Purpose | Files expected to change (new files only unless separately approved) | Validation command | Acceptance criterion | Rollback |
|---|---|---|---|---|---|
| Establish the application workspace and preservation boundary | Isolate future application files from the research workspace and define protected paths. | New directories and a developer/setup note under `<approved-app-root>`; optionally a new root-level ignore file only if required and approved. Do not edit `.idea/.gitignore` or existing IDE settings. | **Proposed:** `Get-ChildItem -Force` at repository root; compare the resulting tree with the approved workspace/path list. Any automated directory check must be newly proposed and reviewed before use. | New files are confined to approved application/tooling paths; no research or Phase 0 path is moved, renamed, or rewritten. | Remove only newly added, specifically approved empty/application-owned paths and files after confirming they contain no user work. Do not use broad recursive cleanup. |
| Add app-scoped dependency manifests and locked toolchain | Make the approved Next.js/TypeScript and FastAPI foundation reproducible without altering research environments. | New frontend/backend manifests and lockfiles under `<approved-app-root>`; no root research dependency file is added or changed. Exact filenames depend on approved package managers. | **Proposed:** `<approved frontend package-manager> <approved frozen-install/check command>` and `<approved Python environment tool> <approved locked-install/check command>`. Exact commands are undecided because no application manifests or package managers exist in the baseline. | Clean setup reproduces only the app environment from reviewed lockfiles; no production credentials or research/model dependencies are required. | Revert/remove only the new app-scoped manifests and lockfiles, preserving any subsequent user edits; do not alter global or research environments. |
| Apply formatting, lint, type, and basic test checks to new application scope | Catch maintainability and correctness issues before product features are added. | New tool configuration and test files under `<approved-app-root>`; any CI definition is new and only at a separately approved CI path. Exact files depend on selected tools. | **Proposed:** `<approved formatter> --check <approved-app-paths>`; `<approved linter> <approved-app-paths>`; `<approved type-check command>`; `<approved test command>`. No such commands are present in the audited baseline. | Checks run reproducibly on app-owned files only, return failure on violations, and do not format or execute notebooks or research assets. CI provider and command names are approved before adoption. | Remove only newly added app-scoped tool configuration/CI files and restore the prior approved toolchain; never run autofix against protected paths. |
| Add minimal provider-independent scaffolding | Prove the selected frontend/backend toolchains start and can be tested without implementing product workflows. | New minimal Next.js/TypeScript and FastAPI app files under `<approved-app-root>`. If approved, include only a neutral frontend shell and process liveness/readiness shell; do not add protected/product endpoints or data contracts. | **Proposed:** `<approved frontend dev/build command>` and `<approved backend test/startup command>`, using local test doubles only. Names and entry points are selected after the toolchain and scaffold are approved. | Scaffold starts/builds in a local test environment without a database, identity provider, external API, model artifact, assistant provider, or production secret. It contains no farmer-data capture or product workflow. | Remove only the new scaffold files after confirming no later work depends on them; do not touch research files or shared IDE settings. |
| Add automated preservation checks | Detect modifications, deletions, or unexpected generated output under protected repository paths. | New checker/test and its baseline mechanism under `<approved-tooling-path>`; optional CI invocation in an approved CI file. The checker and baseline format are proposals and must be reviewed before implementation. | **Proposed static inventory/hash command:** `Get-ChildItem -File -Recurse -Force | Get-FileHash -Algorithm SHA256`; compare paths and hashes to a pre-change baseline captured through an approved, non-research location. No baseline file or checker currently exists. | A controlled test proves a changed, missing, or newly generated protected file fails the preservation check; normal app files are outside the protected set. No notebook is opened or executed. | Remove only the newly added checker/baseline/CI hook if it causes unintended writes; restore protected assets from an independently verified source only with explicit owner approval. Do not auto-restore or overwrite them. |

No autofix, formatter, test discovery, build, or generated-file command may target protected paths. Any command whose scope cannot be proven to exclude those paths is prohibited until corrected and reviewed.

## 3. Explicit exclusions

Phase 1 under this proposal must not implement, stub, or expose:

- Farmer-data capture, account/profile flows, authentication, sessions, role assignment, or authorization workflows.
- Farms, locations, coverage catalogs, or location-dependent features.
- PostgreSQL product entities, schemas, ORM models, or migrations; database connectivity is excluded.
- Export/deletion APIs or user-data lifecycle workflows.
- Expert cases, reviews, consent, or access-grant workflows.
- Model loading/inference, yield predictions, crop rankings, model registry operations, or result history.
- Weather data/features, external data adapters, or mandi-price features.
- An AI assistant, knowledge ingestion, AI-provider calls, or other provider integrations.
- Production secrets integration, containerized public deployment, hosting, public endpoints, or release.

The minimal scaffold may contain local process health checks only if they reveal no sensitive configuration or dependency details. It must not be a public deployment or a product API.

## 4. Preservation rules

The following are immutable during this proposed phase:

- All 22 numbered notebooks: `notebooks/01_project_setup_and_source_registry.ipynb`, `02_apy_dataset_acquisition_and_audit.ipynb`, `03_weather_dataset_acquisition_and_audit.ipynb`, `04_apy_data_overview.ipynb`, `05_apy_data_cleaning.ipynb`, `06_apy_data_preprocessing.ipynb`, `07_apy_eda_analysis.ipynb`, `08_apy_data_visualization.ipynb`, `09_weather_data_overview.ipynb`, `10_weather_data_cleaning.ipynb`, `11_weather_data_preprocessing.ipynb`, `12_weather_eda_analysis.ipynb`, `13_weather_data_visualization.ipynb`, `14_crop_weather_integration.ipynb`, `15_feature_engineering.ipynb`, `16_yield_model_development_and_selection.ipynb`, `17_yield_model_deployment_readiness.ipynb`, `18_crop_recommendation.ipynb`, `19_weather_intelligence.ipynb`, `20_agricultural_risk_intelligence.ipynb`, `21_model_explainability_and_scenarios.ipynb`, and `22_model_registry_and_policy_outputs.ipynb`.
- All notebook checkpoints and notebook-local artifacts.
- Every existing file under `data/`, `models/`, `metadata/`, and `reports/`, including raw/processed datasets, trained artifacts, derived outputs, registries, metadata, and evaluation/audit reports.
- Existing Phase 0 documentation under `docs/architecture/` and `docs/decisions/`, including the audit, specifications, consistency review, P0 resolution plan, implementation backlog, and this scope document once created.
- Existing `.idea/` contents and other pre-existing repository files, unless a separately approved, specifically scoped change is made. Do not treat IDE files as application tooling.

Do not open/save notebooks in a way that changes metadata or outputs; do not format, regenerate, normalize, rename, move, delete, or overwrite protected files. Preserve file paths and bytes. Generated test/build artifacts must stay within the approved application workspace and be ignored by the approved app-only tooling. Preservation verification must compare a pre-change baseline with the post-change tree; a list of filenames alone is insufficient.

## 5. Test strategy and safety limits

- Use only newly added, app-scoped checks and local test doubles. Tests must not require production credentials, a production database, identity provider, weather/AI provider, or external source.
- Test scaffold startup/build, health behavior if included, formatter/linter/type checks, and deterministic unit tests for provider-independent utilities only.
- Validate the preservation checker with a controlled temporary test fixture outside the protected directories. Do not deliberately mutate a research artifact as a test.
- Run dependency/security checks only on newly approved application dependency manifests and files. Any network/package installation requires separate Phase 1 approval; it must not retrieve datasets or research artifacts.
- Do not execute notebooks, import research notebook code, load serialized models, make predictions, download data, or invoke provider APIs.
- Do not claim model, data, API-product, privacy, authorization, or deployment behavior has passed; those components are excluded.
- Preserve test outputs and caches within the app-owned scope. Review every command's working directory and target paths before running it.

## 6. Dependencies and unresolved assumptions

Before implementation begins, the human owners must approve:

- The application workspace boundary and ownership; whether app files are colocated or placed in a new directory.
- Version-control/review baseline and a safe method for recording/comparing protected-file hashes. The repository audit did not find Git metadata at the inspected root.
- Frontend/backend package managers, supported runtime versions, formatting/lint/type/test tools, and dependency/license policy. The audit found no app manifests or existing quality commands.
- CI provider and scope, if CI is included. No CI workflow was found in the baseline.
- Whether minimal health-only scaffolding is needed in this phase and its local-only behavior.
- The exact app paths and preservation-check implementation. Placeholders in this document are not authorized paths or existing scripts.

No provider, database, authentication, model, source, hosting, or public deployment decision is required for this narrow scope. Those choices remain unresolved and out of scope.

## 7. Phase 1 completion criteria and gate

This narrowed foundation phase is complete only when:

1. Human-approved workspace, toolchain, file paths, validation commands, CI scope (if any), and preservation baseline process are recorded.
2. New tooling/scaffolding is limited to the approved application-owned paths and passes its app-scoped formatting, lint, type, test, and reproducible setup/build checks.
3. Automated preservation checks detect a simulated protected-path change using a temporary fixture, and a pre/post baseline comparison shows no existing protected file was changed, added, or deleted by the work.
4. No notebook, dataset, trained artifact, metadata, report, or existing Phase 0 document was reformatted, regenerated, executed, or overwritten.
5. A maintainer confirms the scaffold has no database/provider credentials or integrations and implements none of the excluded product workflows.

Failure of any criterion means Phase 1 foundation is incomplete; do not proceed to Phase 2 under this scope.

**P0 and release status:** Completion of this foundation work does not close or resolve any P0 finding, approve any model/data source or product contract, authorize Phase 2, authorize personal-data collection, or authorize public deployment. All P0 findings and feature-specific gates remain as recorded in `p0-resolution-plan.md` and `consistency-review.md`.
