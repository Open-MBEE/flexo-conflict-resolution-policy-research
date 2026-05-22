# Experiments — Conflict Resolution in Model-Based Systems Engineering

This directory contains 20 experiments that progressively investigate how merge conflicts surface in model-based systems engineering. The first arc (Exp 1–13) starts with a concrete engineering scenario in Flexo MMS, generalizes to arbitrary knowledge graphs, discovers API-layer limitations, and culminates in a three-layer service architecture that separates storage, schema, and verification concerns. The second arc (Exp 14–20) pivots to test whether Git's textual VCS and RDF/SHACL constraint validation form complementary signals for conflict detection — using a refactored satellite model (ADCS + Power) split across team-owned files.

## Experiment Index

| # | Name | API | Model | Key Question | Log |
| --- | --- | --- | --- | --- | --- |
| 1 | [Satellite (local SPARQL)](experiment-1/) | Local Layer 1 | Satellite (SysML) | Baseline: can Flexo detect merge conflicts? | [log](experiment-1/run-output-20260303.log) |
| 2 | [Satellite (remote REST)](experiment-2/) | Remote SysML v2 REST | Satellite (SysML) | Same conflicts via REST API? | [log](experiment-2/run-output-20260318.log) |
| 3 | [MTG-KC instance (local SPARQL)](experiment-3/) | Local Layer 1 | MTG-KC (OWL) | Can Flexo handle non-SysML RDF? | [log](experiment-3/run-output-20260318.log) |
| 4 | [MTG-KC + schema (local SPARQL)](experiment-4/) | Local Layer 1 | MTG-KC + OWL/SHACL | Does Flexo preserve schema triples? | [log](experiment-4/run-output-20260318.log) |
| 5 | [MTG-KC (remote REST)](experiment-5/) | Remote SysML v2 REST | MTG-KC (JSON) | REST API with non-SysML types? | [log](experiment-5/run-output-20260318.log) |
| 6 | [MTG-KC (REST + RDF bridge)](experiment-6/) | Remote REST + pyshacl | MTG-KC (JSON↔RDF) | Can we bridge RDF validation onto REST? | [log](experiment-6/run-output-20260318.log) |
| 7 | [Deletion validation (SysML)](experiment-7/) | Remote SysML v2 REST | Satellite (SysML) | Does identity-only deletion work? | [log](experiment-7/run-output-20260318.log) |
| 8 | [Deletion validation (non-SysML)](experiment-8/) | Remote SysML v2 REST | MTG-KC (non-SysML) | Is deletion type-dependent? | [log](experiment-8/run-output-20260318.log) |
| 9 | [Satellite (remote SPARQL)](experiment-9/) | Remote Layer 1 | Satellite (SysML) | Remote SPARQL matches local? | [log](experiment-9/run-output-20260318.log) |
| 10 | [MTG-KC instance (remote SPARQL)](experiment-10/) | Remote Layer 1 | MTG-KC (OWL) | Remote SPARQL matches local for non-SysML? | [log](experiment-10/run-output-20260318.log) |
| 11 | [MTG-KC + schema (remote SPARQL)](experiment-11/) | Remote Layer 1 | MTG-KC + OWL/SHACL | Remote SPARQL preserves schema? | [log](experiment-11/run-output-20260318.log) |
| 12 | [Three-layer architecture](experiment-12/) | Local Layer 1 | MTG-KC | Where does each concern live? | [log](experiment-12/run-output-20260318.log) |
| 13 | [KC Python API verification](experiment-13/) | Remote Layer 1 | MTG-KC via KC API | Can domain APIs abstract verification? | [log](experiment-13/run-output-20260318.log) |
| 14 | [Git as conflict detector](experiment-14/) | Git + local SPARQL/SHACL | Satellite (ADCS+Power, team-split files) | Does Git catch semantic conflicts across files? | scenario logs in [output/](experiment-14/output/) |
| 15 | [Ontology package versioning](experiment-15/) | Git + local SHACL | Satellite + composable ontology packages | Do independently-evolved packages produce composition conflicts? | scenario logs in [output/](experiment-15/output/) |
| 16 | [Lifecycle branches as stage gates](experiment-16/) | Git + local SHACL | Satellite (Structural→Evidence→Attestation) | Are SHACL-encoded lifecycle gates monotonic? | [log](experiment-16/output/git-log.txt) |
| 17 | [Dual-signal classification](experiment-17/) | Git + local SHACL | Satellite | Does Git+SHACL yield a richer conflict taxonomy than either alone? | scenario logs in [output/](experiment-17/output/) |
| 18 | [Evidence staleness](experiment-18/) | Git + local SHACL + content hashes | Satellite with hash-bound evidence | Can evidence freshness be a SHACL shape spanning RDF + Git? | [log](experiment-18/output/git-log.txt) |
| 19 | [Programmatic reverification](experiment-19/) | Git + local SHACL + oracle re-run | Satellite with proof regeneration | Can a pipeline auto-restore evidence freshness after a model change? | [log](experiment-19/output/git-log.txt) |
| 20 | [The attestation gap](experiment-20/) | Git + local SHACL + human attestation | Satellite (two-stage verification) | What is the irreducible human role after automated reverification? | [log](experiment-20/output/git-log.txt) |

## Narrative Arc

### Stage 1: Baseline — Satellite Power Subsystem (Experiments 1–2)

Two teams independently modify a satellite's communications and thermal subsystems. Each change is individually valid, but combined they violate power budgets, bus load limits, and ownership constraints. Experiment 1 runs this on a local Flexo SPARQL instance; Experiment 2 repeats it on a remote SysML v2 REST API.

**Finding:** Both APIs detect identical conflicts (C2 power +5, C3 bus +5, C6 dual owners, name multiplicity). Conflicts are **commutative** — both application orderings produce the same violations. The conflict is inherent to the model, not the API.

### Stage 2: Generalization — Non-SysML Models (Experiments 3–4)

The satellite model uses SysML-style properties. Can Flexo handle arbitrary RDF? We load the MTG Knowledge Complex — an OWL simplicial complex with 25 elements (5 colors, 10 color pairs, 10 color triples) and topological constraints (boundary-closure, cardinality).

The conflict scenario: one curator removes the Black-Green (Golgari) edge and its dependent faces; another curator enriches that same edge with new properties. Individually valid; combined, the enrichment creates **orphaned triples** — properties on elements that no longer exist in the complex.

**Finding:** Flexo handles arbitrary RDF. But unlike the satellite scenario, this conflict is **non-commutative**: applying delete-then-enrich produces orphans, while enrich-then-delete is clean (SPARQL's wildcard DELETE catches everything). Non-commutativity is itself a conflict signal — the order of application matters.

Experiment 4 adds OWL ontology and SHACL shapes alongside instance data. Flexo preserves them, and schema-aware queries (type consistency, shape target coverage) track structural changes correctly. However, Flexo does **not** run an OWL reasoner — `rdfs:subClassOf` inference doesn't happen server-side.

### Stage 3: API Layer Comparison (Experiments 5–6)

The same MTG-KC structural conflict on the SysML v2 REST API reveals fundamental differences from SPARQL.

**Experiment 5 findings:**
- The REST API is **type-agnostic** — it stores any `@type` and any properties without validation. It functions as a generic versioned JSON document store.
- The REST API has **no native element deletion** — elements persist through commits via inheritance. At the time of this experiment, we had not yet discovered the identity-only commit workaround (see Experiments 7–8). Without deletion, both orderings produce orphans (unlike SPARQL where only one does).
- All constraint checking happens **client-side** — the server contributes nothing to validation.
- The API silently strips namespace prefixes from `@id` values, creating a mismatch between stored IDs and references.

**Experiment 6** layers RDF-native validation (pyshacl + rdflib) on top of the REST API via a JSON↔RDF bridge. The bridge works — SPARQL queries produce identical results client-side — but SHACL baseline violations (from incomplete JSON models) mask conflict-specific signals.

### Stage 4: Deletion Semantics (Experiments 7–8)

We discovered that element deletion IS possible via **identity-only commits** — a pattern from the `flexo_syside` library where a commit's `change` array contains `{"identity": {"@id": "elem-id"}}` with no `payload` key.

**Experiment 7:** Deletion works for SysML v2 types (`PartDefinition`). Deletion is reversible — a subsequent commit can re-create the element.

**Experiment 8:** Initially appeared to fail for non-SysML types, leading to a (wrong) conclusion that deletion was type-dependent. Root cause analysis revealed an **`@id` prefix mismatch**: the API strips `mtg:` from IDs on storage but requires the original prefix for deletion. After fixing the client code, deletion works for all types. With proper deletion, the REST API produces the **same non-commutative conflict signature as SPARQL** (Experiment 3).

### Stage 5: Remote Infrastructure Validation (Experiments 9–11)

Experiments 1, 3, and 4 ran against a local Flexo instance under QEMU emulation. Experiments 9–11 repeat them against a hosted Layer 1 SPARQL endpoint at `try-layer1.starforge.app`.

**Finding:** Results are identical to their local counterparts. The remote service experienced a transient outage (HTTP 504) during testing but recovered. When operational, the remote Layer 1 is functionally equivalent to the local instance — and significantly faster without QEMU overhead.

### Stage 6: Three-Layer Architecture (Experiments 12–13)

The preceding experiments implicitly separated three concerns. Experiment 12 makes the pattern explicit:

```
Layer 3 — VERIFICATION (closed-world constraint checking)
  What is admissible to express. SHACL shapes + SPARQL oracle
  restrict the space of valid states — reject what violates constraints.

Layer 2 — SEMANTIC (open-world ontology packages)
  What can be expressed. OWL classes, properties, and restrictions
  define the vocabulary — anything not contradicted is permitted.

Layer 1 — SYNTACTIC (quadstore)
  What is well-formed. Accepts any valid RDF triples regardless
  of interpretation.
```

Layer 1 accepts any syntactically valid RDF — well-formed triples with valid URIs, literals, and blank nodes. It enforces RDF syntax but is indifferent to semantic interpretation: orphaned properties, violated cardinality constraints, and broken boundary-closure are all syntactically valid RDF that Layer 1 stores without complaint. Only Layer 3, which loads the ontology packages and runs SHACL validation and SPARQL constraint queries, can determine whether a state is semantically valid according to the domain model. The ontology is split into composable packages (kc-core + mtg-domain) that mirror how KerML and SysML v2 domain extensions would be structured.

**Experiment 13** replaces raw pyshacl/SPARQL with the [mtg-kc Python API](https://github.com/mzargham/mtg-kc), which abstracts SHACL and SPARQL behind domain-typed operations (`add_vertex`, `add_edge`, `add_face`, `ValidationError`). This previews how a KerML/SysML v2 verification service would work: the constraint machinery is hidden behind a public API that exposes domain concepts, not violation reports.

### Stage 7: Git + SHACL Dual-Signal Conflict Detection (Experiments 14–20)

Experiments 1–13 used Flexo MMS (an RDF-native VCS) exclusively. Experiments 14–20 invert the question: what happens when **Git** is the version-control layer and **SHACL/SPARQL** runs as a separate constraint-checking layer? The model is refactored from MTG-KC back to a satellite (ADCS + Power subsystems, adapted from [DSG ADCS-lifecycle-demo](https://github.com/DynamicalSystemsGroup/ADCS-lifecycle-demo)) and split across team-owned files (`structural/{satellite,adcs,power}.ttl`, `requirements/...`, `ontology/{rtm,shapes}.ttl`) to mirror real multi-team engineering practice.

**Experiment 14 — Git as conflict detector.** Two teams modify different files. ADCS adds a heavier reaction wheel (+30W); Power reduces available bus margin (−51W). Each change individually stays within budget; together they exceed it by 10W. Git merges cleanly because the edits are in different files. Across a 2×2 confusion matrix (semantic valid/invalid × Git clean/conflict), Git has a **33% false-negative rate** — it misses cross-file semantic conflicts that are coupled through shared constraints.

**Experiment 15 — Ontology package versioning.** When `rtm.ttl` and `shapes.ttl` evolve on independent Git branches, composition conflicts emerge that neither Git nor per-package SHACL catches. Example: RTM consistently renames `rtm:derivedFrom` → `rtm:tracesTo`, while shapes adds a new constraint against the old name. Each branch validates cleanly; Git merges cleanly; the composed graph fails with 6 violations. **Composed SHACL validation is more reliable than static gate queries.**

**Experiment 16 — Lifecycle branches as stage gates.** SHACL shapes encode three lifecycle gates (Structural, Evidence, Attestation). A redesign branch (which removed satisfy links) merges into an already-attested branch, leaving two requirements without structural allocation. The merged state passes Gate 2 but fails Gate 1 — **lifecycle gate compliance is not monotonic**: passing Gate 3 doesn't mean Gate 1 still holds.

**Experiment 17 — Dual-signal classification.** Composing Git's temporal-divergence signal with SHACL's spatial-constraint signal yields a four-way taxonomy: Benign Divergence, Coupling Conflict, Ordering Artifact, Textual Conflict. Git alone collapses benign divergence and coupling conflicts into "clean"; SHACL alone cannot distinguish textual from ordering artifacts. **Coupling conflicts are the most dangerous — invisible to Git, symmetric in SHACL** — and they formalize the false-negative pattern from Experiment 14.

**Experiment 18 — Evidence staleness.** Evidence artifacts carry an `rtm:modelHash` binding them to a model version. A single parameter edit (wheel `maxMomentum` 4.0 → 8.0 N·m·s) invalidates all 6 evidence artifacts and 3 attestations. A `FreshnessShape` compares each evidence's `rtm:modelHash` to the ontology root's `rtm:currentModelHash`. **Evidence freshness is a joint temporal-spatial property** — RDF says which requirements are affected; Git says what changed and when. Neither alone tells the full story.

**Experiment 19 — Programmatic reverification pipeline.** After Experiment 18's parameter change, an automated pipeline re-runs every code-based oracle, regenerates evidence bound to the new model hash, and re-checks the lifecycle gates. Evidence freshness is **RESTORED** (0 stale). 5 of 6 proofs are completely stable (their conclusions don't reference the changed parameter); REQ-002's proof still passes but its margin statement updates. The attestation gate, however, **FAILS** with 6 unattested requirements. The pipeline can automate evidence regeneration but not attestation.

**Experiment 20 — The attestation gap.** Starting from Experiment 19's fresh evidence, an engineer re-attests 5 of 6 requirements and **declines** REQ-001 (pointing accuracy). The proof passes — steady-state error is bounded by `2·tau_gg/Kp`, which doesn't reference wheel momentum — but larger wheels may have different vibration characteristics that couple into star tracker accuracy, and the model doesn't capture this. The `AttestationCompleteShape` correctly fires on REQ-001. **The attestation gap is SHACL-detectable but not SHACL-resolvable** — engineers retain the irreducible role of judging model adequacy.

The mixed-model thesis: **RDF excels at the spatial dimension** (how things relate, compose, and satisfy constraints); **Git excels at the temporal dimension** (who changed what, and when). Composing their signals catches conflicts neither catches alone.

## Cross-Cutting Findings

### Commutativity

| Scenario | API | Commutative? | Notes |
| --- | --- | --- | --- |
| Satellite (Exp 1, 2, 9) | SPARQL, REST | **Yes** | Both orderings produce identical numeric violations |
| MTG-KC (Exp 3, 4, 10, 11) | SPARQL | **No** | delete→enrich has orphans; enrich→delete is clean |
| MTG-KC (Exp 5) | REST (no deletion) | **No** | Both orderings have orphans (API limitation) |
| MTG-KC (Exp 8) | REST (with deletion) | **No** | Matches SPARQL behavior after @id bugfix |
| Satellite cross-file (Exp 14, 17) | Git + SHACL | **Mixed** | Coupling conflicts symmetric under SHACL re-validation; ordering artifacts asymmetric — see Exp 17 taxonomy |

Non-commutativity is a richer conflict signal than simple value disagreement. It indicates that the merge result depends on application order — a property that conflict resolution policies must account for.

### API Comparison

| Capability | Layer 1 SPARQL | SysML v2 REST | Git + SHACL (host filesystem) |
| --- | --- | --- | --- |
| Type validation | None (stores any RDF) | None (stores any JSON) | None (Git is text-only) |
| Constraint evaluation | Server-side (SPARQL SELECT) | Client-side only | Out-of-band (SHACL/SPARQL run separately on the materialized graph) |
| Element deletion | `DELETE WHERE` (native, thorough) | Identity-only commit (not native — workaround discovered in Exp 7–8) | Native (file/line edits + `git rm`) |
| Query capabilities | Full SPARQL | None (fetch all, filter client-side) | None at storage layer (load into rdflib for SPARQL) |
| Schema storage | Preserves OWL/SHACL triples | Not applicable (JSON) | Files committed alongside instance data |
| `@id` handling | Preserves URIs | Strips namespace prefixes | Preserves verbatim |
| OWL reasoning | No | No | No |

### Key Discoveries

1. **Conflicts are model-semantic, not API-dependent** — the same model produces the same conflicts regardless of whether SPARQL or REST is used for storage and querying. But the API *does* change the conflict signature (orphan residue patterns differ).

2. **The SysML v2 REST API is a generic JSON document store** — it accepts any `@type`, any properties, no validation. The "SysML v2" in its name describes its REST conventions, not its type enforcement.

3. **Deletion is possible but not native** — the REST API has no DELETE endpoint for elements. Deletion is achieved via a workaround: identity-only commits (no `payload` key, just `identity`), discovered by reading the `flexo_syside` library source code. Works for all types, but requires the original `@id` (before prefix stripping). Not documented in the API surface.

4. **The `@id` prefix asymmetry** — the API silently strips namespace prefixes on storage but matches against originals for deletion. This caused a bug that initially appeared type-dependent (Exp 8 changelog).

5. **Three-layer separation is natural** — storage (any valid RDF), schema (modular ontology packages), and verification (SHACL + SPARQL) can be cleanly separated. Layer 1 accepts invalid states; only Layer 3 rejects them.

6. **Domain APIs can abstract verification** — the KC Python API hides SHACL/SPARQL behind typed operations, previewing how a production KerML/SysML v2 verification service would work.

7. **Git misses cross-file semantic conflicts** — Git's textual merge sees no overlap when independently-edited files are coupled through a shared constraint (e.g., a power budget spanning ADCS and Power team files). Quantified at a **33% false-negative rate** in Exp 14 and formalized as the Coupling Conflict class in Exp 17.

8. **Lifecycle gate compliance is not monotonic** — passing an attestation gate doesn't mean structural gates still hold. A late change on a separate branch can regress earlier gates after merge, and evidence bound to an old model hash silently goes stale (Exp 16, 18).

9. **Programmatic reverification cannot replace human attestation** — an automated pipeline can re-run code-based oracles and restore evidence freshness to 100%, but the attestation gate remains the engineer's responsibility. Some requirements need new analysis (e.g., vibration coupling not in the model) before they can be attested (Exp 19–20).

## Cross-Experiment Tooling

Experiments 14–20 share infrastructure under [lib/](lib/) and [analysis/](analysis/), managed via [pyproject.toml](pyproject.toml) and [uv](https://docs.astral.sh/uv/).

- [lib/](lib/) — `experiment_logger.py` (dual-output: stdout + structured `output/results.json`), `git_utils.py` (repo orchestration, branching, merging), `rdf_utils.py` (loading, canonical N-Triples hashing, serialization), `shacl_runner.py` (pyshacl wrapper).
- [analysis/](analysis/) — `analyze.py` and `report.py` consume each experiment's `output/results.json` and emit comparison tables (`tables/conflict-detection.{md,csv}`, `tables/signal-effectiveness.{md,csv}`, `tables/temporal-vs-spatial.md`) plus a full `report.md`. The synthesis currently covers Experiments 14–18; 19–20 are documented in their own READMEs.

## How to Reproduce

### Prerequisites

- **Local experiments (1, 3, 4, 12):** Docker/Colima with 12+ GB RAM, local [flexo-mms-deployment](https://github.com/Open-MBEE/flexo-mms-deployment) running
- **Remote REST experiments (2, 5, 6, 7, 8):** `FLEXO_BEARER_TOKEN` env var with token for `experimental.starforge.app`
- **Remote SPARQL experiments (9, 10, 11, 13):** `FLEXO_TOKEN` env var with token for `try-layer1.starforge.app`
- **Python experiments (2, 5, 6, 7, 8, 12, 13):** Python 3.8+, `pip install requests rdflib pyshacl`
- **Mixed-model experiments (14–20):** Python ≥3.9 and [uv](https://docs.astral.sh/uv/). Dependencies (`rdflib`, `pyshacl`, `gitpython`) are managed via [pyproject.toml](pyproject.toml). No Flexo deployment or token is required — the experiments operate on a scratch Git repo and validate RDF directly.
- **All bash experiments:** `curl` and `python3` on PATH

### Environment Variables

```bash
# For remote SysML v2 REST API (experimental.starforge.app)
export FLEXO_BEARER_TOKEN="eyJhbGci..."

# For remote Layer 1 SPARQL API (try-layer1.starforge.app)
export FLEXO_TOKEN="eyJhbGci..."
```

For the mixed-model experiments (14–20), no tokens are needed — install dependencies with uv and run each experiment directly:

```bash
cd experiments
uv sync
uv run python experiment-14/run.py
```

### Suggested Run Order

Local SPARQL experiments require restarting the Flexo stack between runs for clean state:

```bash
cd ~/Documents/GitHub/flexo-mms-deployment/docker-compose
docker compose down && docker compose up -d
# Wait ~60s for Fuseki to initialize
```

1. **Exp 1** → baseline satellite (local SPARQL)
2. **Exp 2** → same scenario, remote REST
3. **Exp 3** → MTG-KC structural conflict (restart Flexo first)
4. **Exp 4** → same + schema (restart Flexo first)
5. **Exp 5–6** → REST API comparison (no restart needed)
6. **Exp 7–8** → deletion validation (no restart needed)
7. **Exp 9–11** → remote SPARQL validation
8. **Exp 12** → three-layer architecture (restart Flexo first)
9. **Exp 13** → KC API verification
10. **Exp 14–18** → Git + SHACL mixed-model experiments (uv-managed, no Flexo restart needed)
11. **Exp 19–20** → reverification pipeline and the attestation gap
12. **analysis/** → run `uv run python analysis/analyze.py` and `uv run python analysis/report.py` to regenerate the cross-experiment tables and synthesis report

## Note on the Knowledge Complex Model

The MTG Knowledge Complex used in Experiments 3–13 is a **toy model** built on a general-purpose [Knowledge Complex (KC) framework](https://github.com/mzargham/mtg-kc). The KC framework enforces canonical mathematical definitions of simplicial complexes — vertices, edges, and faces with boundary operators, cardinality constraints, and closure properties — then extends these abstract topological objects with domain-specific types and attributes. The MTG color wheel (5 colors, 10 color pairs, 10 color triples) serves as a small, self-contained instance for testing.

The KC model family itself (distinct from the MTG toy ontology) is used for scaffolding large knowledge graphs for use with LLMs, where explicit query languages (SPARQL) and constraint enforcement (SHACL) increase auditability and determinism in knowledge retrieval and reasoning. A paper on this approach is forthcoming at INCOSE IS 2026.
