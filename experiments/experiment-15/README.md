# Experiment 15 — Ontology Package Versioning: Composition Conflicts

## Key Question

When composable ontology packages evolve independently on separate Git branches, can their composition produce semantic conflicts that neither Git nor per-package validation detects alone?

## Background

Experiment 12 introduced composable ontology packages (kc-core + mtg-domain) loaded sequentially on a single branch. Experiment 14 showed that Git misses cross-file semantic conflicts. This experiment extends both findings: ontology packages as **independently evolving artifacts** whose composition must be validated.

The satellite model uses two schema packages:
- **`ontology/rtm.ttl`** — RTM vocabulary (classes, properties) → Layer 2 (Semantic)
- **`ontology/shapes.ttl`** — SHACL validation shapes → Layer 3 (Verification)

These map to the three-layer architecture from Experiment 12. Each can be validated in isolation against instance data. But their composition must also be consistent.

## Scenarios

| # | Scenario | Branch A | Branch B | Composed |
|---|----------|----------|----------|----------|
| 1 | Benign | Add `rtm:TestResult` class to rtm.ttl | Add `PartUsageNameShape` to shapes.ttl | PASS (orthogonal) |
| 2 | Property rename | Rename `rtm:derivedFrom` → `rtm:tracesTo` in rtm.ttl + requirements/*.ttl | Add `DerivationChainShape` checking `rtm:derivedFrom` to shapes.ttl | **FAIL** (6 violations — shape references old property name) |
| 3 | New constraint + data | Add `AttributeUnitShape` to shapes.ttl | Add `StarTracker_2` with attribute missing unit to adcs.ttl | **FAIL** (1 violation — new data fails new constraint) |

## Results

### Detection Matrix

| Scenario | Git | Per-package SHACL | Composed SHACL | Composition Gate |
|----------|:---:|:-----------------:|:--------------:|:----------------:|
| Benign | no | no | no | no |
| Property rename | no | no | **YES** (6) | no |
| New constraint + data | no | no | **YES** (1) | no |

**Composition conflicts found: 2** — both invisible to Git and per-package SHACL.

### Key Findings

1. **Composition conflicts are a distinct conflict class.** They are not syntactic (Git sees no overlap), not per-package (each branch validates independently), and only emerge when packages are loaded together. This extends Experiment 14's false-negative finding to the schema layer itself.

2. **Property rename (Scenario 2)** is the canonical case. The RTM team renamed `rtm:derivedFrom` → `rtm:tracesTo` consistently across their files (ontology + instance data). The shapes team wrote a new constraint against the old property name. Git merged cleanly because the branches touched different files. Each branch validated because the shape and the data were each internally consistent. But composed: the shape looks for `rtm:derivedFrom` in data that now uses `rtm:tracesTo` — 6 subsystem requirements all fail.

3. **Schema + data composition (Scenario 3)** is equally dangerous. The shapes team tightened a constraint (`sysml:unit` required on every attribute); the ADCS team added a new component with an attribute missing its unit. Neither change is wrong alone. Only their composition creates a violation.

4. **The composition gate didn't fire** for these scenarios because the gate checks property *declarations* in the ontology, not property *usage* in instance data. The renamed property `rtm:derivedFrom` no longer appears anywhere in the composed graph (it was renamed to `tracesTo` in the data and removed from the ontology). The shape's SPARQL constraint references it but that's embedded in a string literal — invisible to the gate query. This suggests that **composed SHACL validation is a more reliable composition check than static gate queries**, though gates remain useful for simple structural checks.

## How to Run

```bash
cd experiments
uv run python experiment-15/run.py
```

## Connection

- **Experiment 12** introduced composable ontology packages but didn't test independent evolution
- **Experiment 14** showed Git misses cross-file data conflicts; this extends to cross-file schema conflicts
- **Experiment 17** will incorporate this "composition conflict" as a distinct class in the dual-signal taxonomy
