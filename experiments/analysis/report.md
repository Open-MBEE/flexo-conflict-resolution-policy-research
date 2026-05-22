# RDF + Git Mixed Model — Experiment Synthesis Report

*Generated: 2026-04-15 00:08 UTC*

## Executive Summary

These five experiments test the thesis that **RDF and Git are complementary tools** for modeling complex composable engineering systems. RDF excels at the spatial dimension — how things relate, compose, and satisfy constraints. Git excels at the temporal dimension — how things evolve, who changed what, and when.

Using a refactored satellite model (ADCS + Power subsystems, adapted from [dynamical-systems-group/ADCS-lifecycle-demo](https://github.com/dynamical-systems-group/ADCS-lifecycle-demo)), the experiments demonstrate that:

1. **Git misses 33% of semantic conflicts** when teams modify different files that are coupled through shared constraints (Exp 14)
2. **Ontology composition conflicts** are invisible to both Git and per-package validation — only composed SHACL catches them (Exp 15)
3. **Lifecycle gate compliance is not monotonic** — a late structural change can break an earlier gate on an attested branch (Exp 16)
4. **A four-way conflict classification** (benign, coupling, ordering, textual) requires both Git and SHACL signals to distinguish (Exp 17)
5. **Evidence staleness** is a joint temporal-spatial property that spans both RDF provenance and Git commit history (Exp 18)

The mixed model is not about choosing between RDF and Git — it is about using each where it is strongest and composing their signals for richer conflict detection than either provides alone.

## Per-Experiment Findings

### Experiment 14: Git as RDF Conflict Detector — Confusion Matrix

**Question:** Does Git's textual merge produce meaningful conflict signals for RDF?

**Verdict:** MIXED — Git misses semantic conflicts (false negatives)


|                | Sem. Valid | Sem. Invalid |
|----------------|:---------:|:------------:|
| **Git clean**   | 2 (TN) | 2 (FN) |
| **Git conflict**| 0 (FP) | 4 (TP) |

False negative rate: **33%** — Git misses semantic conflicts spanning different files.

### Experiment 15: Ontology Package Versioning — Composition Conflicts

**Question:** Can independently-evolved ontology packages produce composition conflicts invisible to both Git and per-package SHACL?

**Verdict:** CONFIRMED — 2 composition conflict(s) invisible to Git and per-package SHACL


| Scenario | Git | Per-package | Composed | Gate |
|----------|:---:|:----------:|:--------:|:----:|
| benign | no | no | no | no |
| property-rename | no | no | YES | no |
| constraint-data | no | no | YES | no |

### Experiment 16: Lifecycle Branches — Stage Gates as SHACL Shapes

**Question:** Can SHACL shapes encode lifecycle gate prerequisites, and what happens when a late structural change causes regression?

**Verdict:** CONFIRMED — lifecycle regression: late structural change broke gate on attested branch


| Branch | Structural | Evidence | Attestation |
|--------|:----------:|:--------:|:-----------:|
| main | PASS | FAIL | FAIL |
| evidence | PASS | PASS | FAIL |
| attestation | FAIL | PASS | FAIL |
| merged | **FAIL** | PASS | FAIL |

Regression detected: **True**

### Experiment 17: Dual-Signal Conflict Classification (Git + SHACL)

**Question:** Does combining Git + SHACL signals produce a richer conflict classification than either alone?

**Verdict:** CONFIRMED — four-way classification requires both Git and SHACL signals


| Scenario | Git | SHACL(a→b) | SHACL(b→a) | Class |
|----------|:---:|:----------:|:----------:|-------|
| benign | clean | pass | pass | BENIGN_DIVERGENCE |
| coupling | clean | FAIL | FAIL | COUPLING_CONFLICT |
| ordering | CONFLICT | FAIL | pass | ORDERING_ARTIFACT |
| textual | CONFLICT | N/A | N/A | TEXTUAL_CONFLICT |

Classes found: **BENIGN_DIVERGENCE, COUPLING_CONFLICT, ORDERING_ARTIFACT, TEXTUAL_CONFLICT**

### Experiment 18: Evidence Staleness — Provenance Chains Across RDF and Git

**Question:** Can evidence staleness be detected as a SHACL shape, with provenance chains spanning both RDF and Git?

**Verdict:** CONFIRMED — evidence staleness detected after model evolution


| State | Stale Evidence | Stale Attestations |
|-------|:--------------:|:------------------:|
| Before model change | 0 | 0 |
| **After model change** | **6** | **3** |

Model hash changed: `cc0999997597...` → `e415d7bdf7b1...`

### Experiment 19: Programmatic Reverification Pipeline

**Question:** Can a pipeline automatically re-run code-based oracles and restore evidence freshness after model evolution?

**Verdict:** CONFIRMED — pipeline restored evidence freshness; attestation gap remains


| Stage | Stale Evidence | Freshness | Attestation Gate |
|-------|:--------------:|:---------:|:----------------:|
| Pre-reverification | 6 | FAIL | FAIL |
| **Post-reverification** | **0** | **PASS** | **FAIL (6)** |

Proofs re-run: 5 stable, 1 changed (all pass). Evidence freshness restored but attestation gate still fails — human judgment required.

### Experiment 20: The Attestation Gap — Human Judgment Under Model Evolution

**Question:** What is the irreducible human role after programmatic reverification?

**Verdict:** CONFIRMED — attestation gap: 1 requirement(s) have fresh evidence but no attestation. Human judgment is irreducible.


| Requirement | Evidence | Attestation | Status |
|-------------|:--------:|:-----------:|--------|

Pipeline automated 100% of evidence regeneration. Engineer attested 5 of 6 requirements (83%).

**Attestation gap**: REQ-001 — model inadequacy — vibration coupling not modeled. The proof passes but the engineer judges the model may be inadequate.

## Cross-Experiment Synthesis

### The Four-Way Conflict Classification

Experiment 17 formalized a four-way taxonomy. Each earlier experiment demonstrated specific classes:

| Class | Signal Pattern | Demonstrated By |
|-------|---------------|-----------------|
| Benign Divergence | Git clean, both orderings valid | Exp 14 (scenario 1), Exp 17 (scenario 1) |
| Coupling Conflict | Git clean, both orderings invalid | Exp 14 (scenario 2), Exp 15 (scenarios 2-3), Exp 16 (merge regression), Exp 17 (scenario 2) |
| Ordering Artifact | Git conflict, orderings disagree | Exp 17 (scenario 3) — sequential application only |
| Textual Conflict | Git conflict, SHACL N/A | Exp 14 (scenarios 3-4), Exp 17 (scenario 4) |

**Coupling conflicts are the most dangerous class.** They are invisible to Git, symmetric in their SHACL signal, and only caught by domain-specific constraints (power budget, lifecycle gates, composition checks, evidence freshness).

### The Three-Layer Architecture Extended

Experiment 12 (from the original series) identified three layers: Storage, Schema, Verification. Experiments 14-18 extend this:

| Layer | Original (Exp 12) | Extended (Exp 14-18) |
|-------|-------------------|----------------------|
| Storage | Flexo quadstore (accepts any valid RDF) | Git (accepts any valid text files) |
| Schema | OWL ontology packages | RTM ontology + SysMLv2 vocabulary |
| Verification | SHACL shapes + SPARQL oracles | SHACL shapes + SPARQL oracles + Git merge signal + content hashing |

The key extension: **Git's merge signal is a verification input**, not just a storage mechanism. Whether Git reports a conflict or a clean merge is informative — but it is only one of several signals needed for full conflict detection.

### Evidence Freshness as Composed Gate

Experiments 16 and 18 produce shapes that compose naturally:

| Shape | Question | Layer |
|-------|----------|-------|
| StructuralCompleteShape | Has the requirement been allocated? | Lifecycle |
| EvidenceCompleteShape | Has evidence been produced? | Lifecycle |
| AttestationCompleteShape | Has a human attested? | Lifecycle |
| EvidenceFreshnessShape | Is the evidence still valid? | Freshness |
| AttestationFreshnessShape | Is the attestation citing current evidence? | Freshness |

Running all five shapes against a merged state checks both lifecycle completeness AND temporal validity — something no single tool (Git or SHACL alone) can do.

## Design Principles Validated and Refined

### Validated

1. **RDF is primarily spatial; Git is primarily temporal.** This heuristic held across all five experiments. RDF/SHACL detected constraint violations in the merged state (spatial). Git tracked who made what change when (temporal). Neither substituted for the other.

2. **Multi-file model decomposition by team ownership is realistic and reveals coupling.** Splitting the satellite model by subsystem team (ADCS, Power, Systems Engineering) is how real engineering organizations work. It also exposes exactly the coupling conflicts that matter most — cross-team budget violations, interface mismatches, lifecycle regressions.

3. **Declarative constraints (SHACL) compose better than imperative checks.** The ADCS demo's `check_gate()` is Python code. The lifecycle gate shapes from Experiment 16 compose with the freshness shapes from Experiment 18. Composability is a property of the declarative representation, not the constraint content.

### Refined

1. **Git's commutativity is a feature, not a limitation.** Git's 3-way merge is commutative for non-overlapping changes — both merge directions produce the same state. This eliminates ordering artifacts that exist in sequential commit application (Flexo's SPARQL UPDATE). Whether this is desirable depends on context: commutativity reduces false positives but also eliminates a signal (non-commutativity) that can indicate structural coupling.

2. **The "composition gate" (static cross-package check) is less powerful than composed SHACL validation.** Experiment 15's composition gate query didn't fire because the renamed property was embedded in SPARQL strings inside SHACL constraints — invisible to static analysis. Running the composed SHACL shapes against instance data is more reliable because it tests actual behavior, not declared structure.

3. **Evidence staleness is conservative by design.** All 6 evidence artifacts became stale from a single parameter change (Experiment 18). This is correct: any structural change could invalidate any proof's assumptions. A more granular approach (per-requirement model dependency tracking) would reduce false staleness but requires explicit dependency declarations that the current model doesn't have.

## Comparison with Experiments 1-13

| Aspect | Experiments 1-13 (Flexo) | Experiments 14-20 (Git + RDF) |
|--------|--------------------------|-------------------------------|
| VCS | Flexo MMS (RDF-native) | Git (text-oriented) |
| Conflict detection | Server-side SPARQL + client-side pyshacl | Client-side SHACL + SPARQL + Git merge signal |
| Commit format | SPARQL UPDATE patches | File-level text diffs |
| Ordering sensitivity | Non-commutative (DELETE then INSERT ≠ INSERT then DELETE) | Commutative for non-overlapping files; non-commutative only for sequential application |
| Model domain | MTG Knowledge Complex (simplicial complex) | Satellite ADCS + Power (SysMLv2 engineering model) |
| Key finding (shared) | Conflicts are model-semantic, not API-dependent | Same: conflicts are model-semantic, not VCS-dependent |
| Key finding (new) | Three-layer architecture (storage, schema, verification) | Git's merge signal is an additional verification input; evidence freshness as joint temporal-spatial property |

## Open Questions

1. **Granular staleness tracking.** Can per-requirement model dependencies reduce false staleness without requiring explicit dependency declarations? Could SHACL path expressions or SPARQL property chains infer which requirements are affected by a specific structural change?

2. **Automated conflict resolution.** Experiments 14-18 detect conflicts but don't resolve them. The constrained optimization formalism from the original research (Lagrange duality, shadow prices) could be applied to the Git + RDF setting — but the merge operation would need to produce RDF-aware diffs, not text diffs.

3. **CI/CD integration.** The lifecycle gate shapes (Experiment 16) and freshness shapes (Experiment 18) are natural CI gate checks. How should they be wired into a Git-based CI pipeline? Should they run pre-merge (blocking) or post-merge (advisory)?

4. **Scaling to larger models.** The satellite model has ~500 triples across 6 files. Real SysMLv2 models can have millions of triples across hundreds of files. How does the multi-file decomposition strategy scale? Does SHACL validation become a bottleneck?

5. **Canonical serialization.** Experiment 14 showed that Turtle serialization nondeterminism causes Git false positives. Should engineering models enforce canonical serialization (sorted N-Triples, deterministic Turtle)? What are the tooling implications?
