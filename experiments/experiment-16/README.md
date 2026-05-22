# Experiment 16 — Lifecycle Branches: Stage Gates as SHACL Shapes

## Key Question

When Git branches represent lifecycle stages, can SHACL shapes encode stage gate prerequisites — and what happens when a late structural change merges into an attested branch?

## Background

The [dynamical-systems-group/ADCS-lifecycle-demo](https://github.com/dynamical-systems-group/ADCS-lifecycle-demo) implements an 8-stage lifecycle pipeline with gates enforced imperatively in Python (`check_gate()`). This experiment makes those gates **declarative SHACL shapes** — the same verification machinery used for topological constraints in Experiments 4, 11, and 12.

**Thesis:** Lifecycle progression is a temporal concern (Git branch topology captures stage ordering). Gate compliance is a spatial concern (the RDF graph at each stage must satisfy stage-specific shapes). A late structural change can break an earlier gate on a branch that had already passed later gates — lifecycle regression.

## Lifecycle Gate Shapes

| Gate | Shape | Checks |
|------|-------|--------|
| 1. Structural | `StructuralCompleteShape` | Every subsystem requirement has a satisfy link |
| 2. Evidence | `EvidenceCompleteShape` | Every subsystem requirement has evidence addressing it |
| 3. Attestation | `AttestationCompleteShape` | Every subsystem requirement has a human attestation |

Each gate subsumes the previous: passing Gate 3 implies Gates 1 and 2 must also pass.

## Procedure

1. **main** branch: commit structural model + requirements. Gate 1 passes; Gates 2–3 fail (expected — no evidence yet).
2. **evidence** branch: add proof artifacts. Gates 1–2 pass; Gate 3 fails (no attestations).
3. **attestation** branch: add human attestations. Gates 1–2 pass; Gate 3 fails only for REQ-001 (deliberately unattested, mirrors ADCS demo).
4. **redesign** branch (from main): remove StarTracker from REQ-001 allocation; remove REQ-P01/P02 satisfy links (power architecture redesign).
5. Merge **redesign** into **attestation** via Git → **clean merge** (different files).
6. Run gates on merged state: **Gate 1 FAILS** — lifecycle regression.

## Results

### Stage-by-Branch Compliance Matrix

| Branch | Structural | Evidence | Attestation |
|--------|:----------:|:--------:|:-----------:|
| main | PASS | FAIL (6) | FAIL (6) |
| evidence | PASS | PASS | FAIL (6) |
| attestation (pre-merge) | PASS | PASS | FAIL (1) |
| **merged** | **FAIL (2)** | PASS | FAIL (1) |

### Regression Detail

After merging the redesign branch into the attested branch:
- `pwr:REQ-P01` — STRUCTURAL GATE FAIL: no satisfy links (power architecture redesign removed them)
- `pwr:REQ-P02` — STRUCTURAL GATE FAIL: same reason

Git merged cleanly because the redesign modified `requirements/power.ttl` while the attestation branch only added `evidence/` files. No textual overlap. But the merged state has an attested branch where two requirements lack structural allocation — a lifecycle regression.

### Key Findings

1. **Lifecycle gate compliance is not monotonic.** A branch can pass Gate 3 (attestation) and then regress to failing Gate 1 (structural) after a merge. This is a conflict type Experiments 1–13 did not explore.

2. **SHACL shapes make gates declarative and composable.** Unlike imperative `check_gate()`, SHACL shapes can be combined with other constraints (power budgets from Exp 14, composition checks from Exp 15) and evaluated at merge time by any tool that speaks SHACL.

3. **Git sees no conflict** because the structural change and the evidence/attestation additions live in different files. This is the same false-negative pattern as Experiment 14, extended to the lifecycle dimension.

## How to Run

```bash
cd experiments
uv run python experiment-16/run.py
```

## Connection

- **DSG/ADCS-lifecycle-demo**: gates were imperative Python; now declarative SHACL
- **Experiment 14**: same false-negative pattern (cross-file coupling invisible to Git)
- **Experiment 17**: lifecycle regression becomes a conflict class in the dual-signal taxonomy
- **Experiment 18**: composes lifecycle gates with evidence freshness checks
