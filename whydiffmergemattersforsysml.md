# Why Strong Diff/Merge Matters for SysML Models

## Summary

As soon as SysML models move from being optional documentation to becoming the engineering **source of truth**, strong diff and merge stops being a nice-to-have and becomes core infrastructure.

Multiple engineers must be able to change the model in parallel, review those changes, understand exactly what changed, and safely reintegrate accepted work into a consistent baseline.

Without strong model-aware diff and merge, MBSE does not scale well beyond isolated experts or small teams.

## Why Strong Diff/Merge Is Needed

### 1. SysML models are structured engineering knowledge, not just files
A SysML model contains elements, relationships, interfaces, allocations, dependencies, requirements links, and views  these models are graphs after all. A simple file-level diff cannot explain changes in a way that engineers can evaluate. Teams need to compare the *meaningful structure* of the model.

### 2. Parallel work is unavoidable in real MBSE
In real projects, multiple people work on architecture, requirements, interfaces, behaviors, and verification aspects at the same time. That means models must support branching, isolated changes, controlled reintegration, and conflict resolution.

### 3. Review and auditability are essential
In regulated and safety-relevant environments, it is not enough to know the latest version of the model. Teams also need to know:

- who changed what
- when it changed
- why it changed
- whether it was reviewed
- which baseline or release contains the change

Strong diff/merge is therefore part of governance, not just productivity.
> "effective measures of versions control"

### 4. MBSE must work like modern software engineering
Organizations want to treat models more like code, using version control, branching, reviews, builds, releases, and automated integration. This only works if models can be compared and merged reliably at model level.

### 5. Large models must be modular and reusable
As systems grow, teams need to split models into components or packages, manage them with separate ownership and lifecycles, and still integrate them into an overall system baseline. This creates dependency and merge challenges that require strong tooling.

## What Capabilities Are Needed

### Semantic diff
The tool must compare **model semantics**, not just text or binary file changes. It should show differences in:

- elements
- properties
- relationships
- package structures
- diagrams and views
- trace links

### Three-way merge
To support parallel work, the tool must perform proper **three-way merge** and distinguish between:

- non-overlapping changes that can be merged automatically
- real conflicts that need human resolution

### Conflict detection and resolution support
When two people change the same model element or create contradictory changes, the tooling must clearly identify the conflict and help resolve it safely.

### Preservation of model consistency
A merge result must preserve references, structure, and overall model validity. It must not silently break dependencies or corrupt the model.

### Fine-grained traceability
Teams need detailed change history at model level, including:

- changed element
- type of change
- author
- revision
- timestamp
- relationship to change request, review, or release

> Easy to realize if changes are organized in "commits" - the metadata can be kept outside the Model

### Review support for changes
Reviewers need to inspect **deltas**, not only final model states. Useful capabilities include:

- filtered change lists
- review comments on changes
- pause/resume review
- review status tracking
- export of review evidence

### Integration with version-control workflows
Strong model diff/merge should work with normal engineering workflows such as:

- Git or SVN repositories
- branches
- pull/merge requests
- release branches
- tagged baselines

### ~~Dependency analysis~~
~~For modularized models, teams need visibility into dependencies between components, including cross-component references and unwanted coupling such as circular dependencies.~~

### ~~Support for modularization and reuse~~
~~The tooling should support model components, package-level versioning, reuse across projects, and controlled reintegration into a larger system model.~~

### Automation in build pipelines
Modern MBSE increasingly needs automation similar to CI/CD for code. Useful capabilities include:

- automated diff generation
- automated merge
- merge previews
- conflict reporting
- baseline updates
- integration into build servers and delivery workflows

### Baseline and release management
Teams must be able to define stable model baselines and released states, and to relate those states to product configurations, variants, and product-line development.

### Understandable outputs for broader stakeholders
Diff/merge results must be understandable not only for expert modelers but also for reviewers, architects, leads, and other stakeholders who rely on the model but do not directly edit it.

### Commercial proof point

> The need for strong diff/merge exists because MBSE becomes operationally fragile without it.

LemonTree is useful as a **commercial proof point** that this is a real industrial need. Companies adopt such tooling because they need model comparison, merging, traceability, dependency handling, review support, and integration with normal version-control and build workflows.

## Executive Summary

Strong diff and merge is essential for SysML models because, in real MBSE, the model is not a static document but a living engineering baseline shared by many people across disciplines. Once models become the source of truth, teams need to branch, compare, review, merge, release, and audit model changes with the same rigor as source code, but with model-aware semantics. The required capabilities therefore include semantic diff, three-way merge, conflict detection, consistency preservation, traceability, review support, ~~dependency analysis, modularization,~~ and automation in version-control and build workflows. LemonTree is relevant  as evidence that industry has already recognized this need and invested in dedicated solutions.

