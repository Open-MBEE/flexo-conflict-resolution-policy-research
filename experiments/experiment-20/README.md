# Experiment 20 — The Attestation Gap: Human Judgment Under Model Evolution

## Key Question

After programmatic reverification restores evidence freshness (Experiment 19), what is the irreducible human role? Can SHACL detect the gap between "evidence passes" and "requirement satisfied"?

## Background

The [DSG ADCS-lifecycle-demo](https://github.com/DynamicalSystemsGroup/ADCS-lifecycle-demo) establishes the core epistemological principle:

> "Evidence does not verify requirements; evidence supports a human judgment that requirements are satisfied."

Experiment 19 showed that a pipeline can automatically regenerate all evidence after a model change. But evidence freshness is necessary, not sufficient. The engineer must still judge:
- **Model adequacy**: Is the model an adequate representation for this requirement?
- **Evidence sufficiency**: Does the computational evidence support the requirement?

This experiment demonstrates the gap.

## Procedure

Starting from Experiment 19's output (model v2, fresh evidence, no attestations):

1. Engineer reviews all 6 requirements against fresh evidence
2. **5 requirements re-attested**: REQ-002 (with revised margin statement), REQ-003, REQ-004, REQ-P01, REQ-P02
3. **1 requirement declined**: REQ-001 (pointing accuracy)
4. Check lifecycle gates: AttestationCompleteShape fires on REQ-001

## Results

### Attestation Status

| Requirement | Evidence | Attestation | Status |
|-------------|:--------:|:-----------:|--------|
| REQ-001 | fresh | **DECLINED** | GAP — needs vibration analysis |
| REQ-002 | fresh | revised | CLOSED — margin noted |
| REQ-003 | fresh | confirmed | CLOSED |
| REQ-004 | fresh | confirmed | CLOSED |
| REQ-P01 | fresh | confirmed | CLOSED |
| REQ-P02 | fresh | confirmed | CLOSED |

### The REQ-001 Attestation Gap

The pointing accuracy proof passes: steady-state error is bounded by `2*tau_gg/Kp`, which doesn't depend on wheel momentum capacity. The pipeline says "proof passes."

But the engineer declines to attest because **the model may be inadequate**: larger reaction wheels (8.0 N.m.s vs. 4.0 N.m.s) may have different vibration characteristics that couple into star tracker accuracy. The pointing proof doesn't model this coupling. The proof is correct *within the model*, but the model itself may no longer be adequate for the physical system.

This is exactly the distinction the ADCS demo makes between `rtm:addresses` (evidence addresses a requirement — structural intent) and `rtm:attests` (human judgment that the requirement is satisfied).

### Key Findings

1. **The attestation gap is SHACL-detectable but not SHACL-resolvable.** `AttestationCompleteShape` fires on REQ-001, identifying the gap. But no automation can fill it — the engineer must either:
   - Commission additional analysis (vibration coupling model)
   - Apply engineering judgment (vibration is negligible for this wheel size)
   - Request hardware testing (measure actual vibration spectrum)

2. **Programmatic reverification handles 100% of evidence but only 83% of attestations.** The pipeline automated all evidence regeneration (Exp 19). The engineer attested 5 of 6 requirements. The remaining 1 requires work that doesn't yet exist in the model.

3. **Revised attestations carry information that automation cannot generate.** The REQ-002 re-attestation includes an updated adequacy statement noting the doubled margin. This is engineering knowledge about the *significance* of the change — not just whether the proof passes, but what the new margin means for the design. No pipeline can generate this statement.

4. **The gap is a feature, not a bug.** The SHACL shape correctly identifies that REQ-001 lacks attestation. The fact that the pipeline cannot close this gap is by design — it ensures that a human engineer has reviewed each requirement against the current model before it's considered satisfied. Automating this away would be epistemologically wrong.

## How to Run

```bash
cd experiments
uv run python experiment-20/run.py
```

## Connection

- **Experiment 18**: staleness detection (the problem)
- **Experiment 19**: programmatic reverification (the automated solution)
- **This experiment**: the human residual (what automation cannot do)
- **DSG/ADCS-lifecycle-demo**: the epistemological framework (evidence ≠ verification)
