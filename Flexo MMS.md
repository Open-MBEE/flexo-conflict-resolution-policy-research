# Flexo MMS

Flexo MMS is a [version control system for structured data](https://flexo-mms-deployment-guide.readthedocs.io/en/latest/) from [OpenMBEE](https://github.com/open-mbee). It provides a [graph-native approach to storing and diff'ing models](https://www.openmbee.org/flexo.html), handling models as [[RDF]] graphs and exposing [[SPARQL]] and [[Graph Store Protocol]] (GSP) endpoints for model update/load/query operations, as well as CRUD endpoints for management of RDF graphs ([Architecture](https://openmbee.atlassian.net/wiki/spaces/OPENMBEE/pages/320765953/Flexo-MMS+Architecture)).

Models in Flexo are not limited to enterprise model development platforms — it can store anything expressed as RDF ([openmbee.org](https://www.openmbee.org/flexo.html)).

## Engineering Operations Levels

Flexo's governance and workflow responsibilities are organized into four operational levels, each with a distinct scope and set of concerns. The levels describe *who* interacts with the system and what decisions they make.

| Level            | Concern                                                              | Note                                   |
| ---------------- | -------------------------------------------------------------------- | -------------------------------------- |
| 1 — Ecosystem    | Organizations sharing model assets across enterprise boundaries      | [[Flexo Ecosystem Level]]              |
| 2 — Organization | IT/platform team maintaining Flexo for the enterprise                | [[Flexo Organization Level]]           |
| 3 — Team         | Engineering team developing and maintaining specific model assets    | [[Flexo Team Level]]                   |
| 4 — Individual   | Engineer proposing, evaluating, or merging changes to model elements | [[Flexo Individual Contributor Level]] |

## Architectural Layers

The operational levels above describe *who* interacts with Flexo and at what scope. The architectural layers below describe *how* data flows through the system. The two hierarchies are orthogonal: an individual contributor interacts via the SysML v2 API, but their request traverses all four layers.

| Layer            | Component                                                                         | Protocol                                                            | Responsibility                          | Note                                   |
| ---------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------- | --------------------------------------- | -------------------------------------- |
| 3 — Client       | VSCode, Jupyter, Cameo MDK, scripts                                               | HTTP/REST                                                           | Model editing, visualization, analysis  | [[Flexo Individual Contributor Level]] |
| 2 — SysML v2 API | [flexo-mms-sysmlv2](https://github.com/Open-MBEE/flexo-mms-sysmlv2)               | REST/JSON (OMG PSM)                                                 | Domain-typed CRUD, merge, diff, query   | [[SysML v2]]                           |
| 1 — Layer 1      | [flexo-mms-layer1-service](https://github.com/Open-MBEE/flexo-mms-layer1-service) | [[SPARQL]], [[Graph Store Protocol]], [[Linked Data Platform\|LDP]] | Version-controlled RDF graph management | [[Flexo Organization Level]]           |
| 0 — Quadstore    | [[Apache Jena Fuseki]] (or compatible)                                            | SPARQL 1.1                                                          | Persistent storage of named graphs      | [[Quadstore]]                          |

## Standards

→ [[Standards Reference]]

## Governance Concepts

- [[Verification and Validation]] — what can be checked mechanically vs what requires judgment
- [[Rules and Norms]] — how governance mechanisms manifest across operational layers
- [[Policy]] — locally-imposed, tailorable rules that bridge norms to enforcement
- [[Continuous Integration]] — the mechanism that enforces verification-scope rules and policies

## Conflict Resolution

- [[Model]] — what "model" means in SE and in Flexo storage
- [[Diff and Delta]] — how Flexo computes and stores differences between model states
- [[Merge]] — integrating changes from divergent branches
- [[Conflict Classification]] — taxonomy of conflict types and constraint categories
- [[Predicate Compliance Oracle]] — abstract constraint evaluator; conceptual hook for dual variables

### Experiments

- [[Experiment 1 — Satellite Scenario]] — cross-application conflict detection on a constraint-rich satellite model (syntactic, structural, semantic conflicts)

→ [[Key Insight]] · [[Flexo Conflict Resolution Mapping]] · [[Conflict Resolution Problem Statement]] · [[A Policy-based Approach to Model Lifecycle Management with Flexo|Model Lifecycle Diagrams]]

## Key Repositories

- [flexo-mms-layer1-service](https://github.com/Open-MBEE/flexo-mms-layer1-service) — core service, SPARQL/GSP API
- [flexo-mms-sysmlv2](https://github.com/Open-MBEE/flexo-mms-sysmlv2) — OMG [[SysML v2]] API implementation
- [flexo-mms-deployment](https://github.com/Open-MBEE/flexo-mms-deployment) — Docker Compose / k8s deployment → [[Local Deployment Setup]]
- [Layer 1 OpenAPI spec](https://www.openmbee.org/flexo-mms-layer1-openapi/) — CRUD API surface
