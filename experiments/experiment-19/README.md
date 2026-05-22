# Experiment 19 — Programmatic Reverification Pipeline

## Key Question

After a structural model change invalidates all evidence (Experiment 18), can a pipeline automatically re-run code-based oracles, regenerate evidence, and restore evidence freshness without human intervention?

## Background

Experiment 18 showed that a single parameter change (wheel maxMomentum 4.0 → 8.0 N.m.s) made all 6 evidence artifacts and 3 attestations stale. This experiment tests the automated recovery path: re-running every proof and analysis against the evolved model.

## Procedure

| Stage | Action | Result |
|-------|--------|--------|
| 1 | Commit structural model v1 | model_hash_v1 |
| 2 | Add evidence bound to v1 | 6 evidence artifacts |
| 3 | Evolve model (momentum 4.0 → 8.0) | model_hash_v2, all evidence stale |
| 4 | Detect staleness | SHACL: 6 stale evidence |
| 5 | Re-run proofs (simulated) | 5 stable, 1 changed (all pass) |
| 6 | Generate fresh evidence bound to v2 | 6 new evidence artifacts |
| 7 | Check freshness | **RESTORED** (0 stale) |
| 8 | Check lifecycle gates | **FAIL** (6 attestation violations) |

## Results

### Proof Stability Analysis

| Requirement | Depends On | Conclusion | Changed? |
|-------------|-----------|------------|:--------:|
| REQ-001 pointing | Kp, Kd, tau_gg | Error bounded by 2*tau_gg/Kp | no |
| REQ-002 momentum | Kd, Kp, J, maxMomentum | Peak < 4.0 N.m.s | **yes** (margin doubled) |
| REQ-003 stability | Kp, Kd, J | Routh-Hurwitz satisfied | no |
| REQ-004 disturbance | maxTorque, orbitalRate, J | Torques micro-Nm | no |
| REQ-P01 power | panel, PDU, draws | 306W > 300W | no |
| REQ-P02 eclipse | battery, voltage, DOD | 672Wh > 282Wh | no |

5 of 6 proofs are completely stable (their conclusions don't reference the changed parameter). REQ-002's proof still passes but the margin statement is updated because the hardware capacity doubled.

### Key Finding

**The pipeline can automate evidence regeneration but not attestation.**

- Evidence freshness: **RESTORED** (0 stale after reverification)
- Attestation gate: **FAIL** (6 requirements unattested)

The pipeline successfully: detected staleness, re-ran proofs, determined which conclusions changed, generated fresh evidence bound to the new model version. But it cannot issue attestations — that requires human judgment about model adequacy and evidence sufficiency.

This sets up Experiment 20: the irreducible human role.

## How to Run

```bash
cd experiments
uv run python experiment-19/run.py
```

## Connection

- **Experiment 18**: staleness detection (this experiment's starting point)
- **Experiment 20**: the attestation gap (what automation cannot do)
- **DSG/ADCS-lifecycle-demo**: the proof re-execution pattern (`reproduce.py`)
