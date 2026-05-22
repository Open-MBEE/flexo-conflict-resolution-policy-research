# Experiment 18 — Evidence Staleness: Provenance Chains Across RDF and Git

## Key Question

When evidence is hash-bound to a model version and the model subsequently evolves, can staleness detection be encoded as a SHACL shape — and can provenance chains span both RDF (traceability graph) and Git (commit history)?

## Background

The [DSG ADCS-lifecycle-demo](https://github.com/DynamicalSystemsGroup/ADCS-lifecycle-demo) binds evidence to model versions via `rtm:modelHash` and `rtm:gitCommit`, using deterministic SHA-256 hashing of canonical N-Triples. But the demo runs as a single pipeline execution — it never tests what happens when the model evolves *after* evidence is bound.

This experiment introduces model evolution and tests whether the freshness property can be checked declaratively via SHACL, and whether the full provenance chain (which requirements are affected, who attested them, what changed, when) spans both RDF and Git.

## Procedure

| Stage | Action | Gate Result |
|-------|--------|-------------|
| 1. STRUCTURAL | Commit satellite model | — |
| 2. EVIDENCE | Bind proof artifacts to model hash v1 | Freshness: PASS |
| 3. ATTESTATION | Add human attestations citing evidence | Freshness: PASS |
| 4. DESIGN UPDATE | Change wheel maxMomentum 4.0 → 8.0 N.m.s | **Freshness: FAIL** |

The design update changes the structural model (commit `7a711fbc`), producing a new model hash (v2). The evidence is still bound to hash v1. The `currentModelHash` is updated to v2, causing the freshness shape to fire on all 6 evidence artifacts and 3 attestations.

## Results

### Freshness Check

| State | Evidence Fresh | Attestations Fresh |
|-------|:--------------:|:------------------:|
| Before design update | 6/6 | 3/3 |
| **After design update** | **0/6** | **0/3** |

### Staleness Provenance Chain

For each stale attestation, the combined RDF + Git provenance identifies:

```
Requirement: REQ-002
  Attestation: ATT-REQ-002
    Attested by: Dr. Michael Zargham
    Attested at: 2026-04-14T23:32:06Z
  Evidence: EV-PROOF-REQ-002
    Bound to model: cc09999975... (v1)
    Current model:  e415d7bdf7... (v2)
  Git history:
    Evidence created: commit 0880fa10
    Model changed:   commit 7a711fbc
    Change: wheel maxMomentum 4.0 -> 8.0 N.m.s
```

**RDF tells you:** which requirements are affected, who attested them, what evidence was cited, and that the model hash doesn't match.

**Git tells you:** what specifically changed in the structural model, when it changed, and who made the change.

**Neither alone tells the full story.** RDF sees the hash mismatch but not the structural diff. Git sees the diff but doesn't know which requirements or attestations are affected.

### Key Findings

1. **Evidence freshness is a joint temporal-spatial property.** The temporal dimension (model changed at commit X) has spatial consequences (requirements Y and Z are now backed by stale evidence). SHACL encodes the spatial check; Git provides the temporal context.

2. **The freshness SHACL shape composes with Experiment 16's lifecycle gates.** Together they enforce:
   - `EvidenceCompleteShape`: "has evidence been provided?" (lifecycle gate)
   - `EvidenceFreshnessShape`: "is that evidence still valid?" (freshness gate)
   - `AttestationFreshnessShape`: "are attestations citing current evidence?" (freshness gate)

3. **Content hashing provides the bridge.** The `rtm:modelHash` property binds evidence to a specific model version. The `rtm:currentModelHash` property on the ontology root tracks the current version. SHACL compares them. This is the same pattern as the ADCS demo's `hash_structural_model()`, now made declarative.

4. **All 6 evidence artifacts and 3 attestations become stale from a single parameter change.** Even though only `maxMomentum` changed (one attribute on one component), every proof was bound to the same model hash. This is correct: any structural change could invalidate any proof's assumptions. A more granular staleness model could track per-requirement model dependencies, but the conservative approach (all evidence stale on any change) is safer.

## SHACL Shapes

### EvidenceFreshnessShape
```
Target: rtm:Evidence
Check: rtm:modelHash must equal rtm:currentModelHash on the ontology root
```

### AttestationFreshnessShape
```
Target: rtm:Attestation
Check: all cited evidence (rtm:hasEvidence) must have matching model hashes
```

## How to Run

```bash
cd experiments
uv run python experiment-18/run.py
```

## Connection

- **DSG/ADCS-lifecycle-demo**: evidence hashing and provenance binding (single pipeline, no evolution)
- **Experiment 16**: lifecycle gates (structural, evidence, attestation) — freshness extends these
- **Experiment 14**: false negatives from cross-file coupling — staleness is a temporal variant of coupling
- This is the **capstone experiment** for the mixed model thesis: the provenance chain spanning RDF and Git is the most concrete demonstration that neither tool alone captures the full traceability picture
