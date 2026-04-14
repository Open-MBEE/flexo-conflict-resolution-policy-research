# Experiment 17 — Dual-Signal Conflict Classification (Git + SHACL)

## Key Question

Does combining Git's temporal divergence signal with RDF's spatial constraint signal produce a richer conflict classification than either alone?

## Background

Experiments 3–4 showed non-commutativity is a richer signal than value disagreement. Experiment 14 showed Git misses cross-file semantic conflicts. This experiment formalizes a **four-way classification** using both signals:

| Class | Git merge | SHACL (u→v) | SHACL (v→u) | Meaning |
|-------|:---------:|:-----------:|:-----------:|---------|
| Benign Divergence | clean | pass | pass | Independent changes |
| Coupling Conflict | clean | fail | fail | Coupled subsystems, both orderings break |
| Ordering Artifact | clean/conflict | fail | pass (or vice versa) | Non-commutative — order matters |
| Textual Conflict | conflict | N/A | N/A | Same text modified |

## Scenarios

| # | Scenario | Branch A | Branch B | Result |
|---|----------|----------|----------|--------|
| 1 | Benign | ADCS tunes PD gains | Power relaxes battery DOD | Git clean, both valid |
| 2 | Coupling | ADCS upgrades wheels (+30W) | Power reduces panels (-51W avail) | Git clean, both **INVALID** (265W > 255W) |
| 3 | Ordering | ADCS sets draw=70W | Power sets available=250W + draw=55W | Git CONFLICT; sequential A→B **INVALID** (255W > 250W), B→A valid (240W < 250W) |
| 4 | Textual | ADCS sets draw=55W | SysEng sets draw=48W | Git CONFLICT |

### Ordering Artifact (Scenario 3) — Sequential Application

Git's 3-way merge is commutative for non-overlapping file changes, so ordering artifacts cannot emerge from Git merge alone. However, **sequential application** (apply one branch's changes, then the other's on top) can be non-commutative — the same pattern as Flexo's SPARQL UPDATE ordering from Experiments 1–13.

In this scenario, both branches modify `adcs.ttl` (setting different power draw values), so Git conflicts. But testing sequential application:
- **A then B**: Branch A sets draw=70W, then Branch B's mutation targets the original value "50.0" → doesn't match → draw stays 70W → total 255W > 250W available → **FAIL**
- **B then A**: Branch B sets draw=55W, then Branch A's mutation targets "50.0" → doesn't match → draw stays 55W → total 240W < 250W → **PASS**

The last-writer-wins semantics produce different constraint outcomes depending on application order.

## Results

### Classification Summary

| Scenario | Git | SHACL(a→b) | SHACL(b→a) | Class |
|----------|:---:|:----------:|:----------:|-------|
| benign | clean | pass | pass | BENIGN_DIVERGENCE |
| coupling | clean | FAIL | FAIL | COUPLING_CONFLICT |
| ordering | CONFLICT | FAIL | pass | ORDERING_ARTIFACT |
| textual | CONFLICT | N/A | N/A | TEXTUAL_CONFLICT |

### Signal Distinguishing Power

| Signal | Distinct classes |
|--------|:----------------:|
| Git alone | 2 (clean vs. conflict) |
| SHACL alone | 4 (both_pass, both_fail, asymmetric, N/A) |
| **Combined** | **4** |

### Key Findings

1. **The four-way classification requires both signals.** Git alone collapses benign divergence and coupling conflicts into "clean." SHACL alone cannot distinguish textual conflicts from ordering artifacts (both show partial N/A). Only the combination disambiguates all four classes.

2. **Git's commutativity eliminates ordering artifacts for non-overlapping changes.** When branches modify different files, Git merge produces the same state regardless of direction. Ordering artifacts only appear in sequential application (rebasing, cherry-picking) or when branches touch the same file. This contrasts with Flexo's SPARQL UPDATE where commit ordering always matters.

3. **Coupling conflicts are the most dangerous class.** They are invisible to Git (clean merge), symmetric in SHACL (both orderings fail identically), and only caught by domain-specific constraint queries (power budget oracle). This is the class Experiment 14 identified as "false negatives."

## How to Run

```bash
cd experiments
uv run python experiment-17/run.py
```

## Connection

- **Experiments 1–13**: non-commutativity as a conflict signal (Flexo/SPARQL)
- **Experiment 14**: false negatives = coupling conflicts in this taxonomy
- **Experiment 15**: composition conflicts are a variant of coupling conflicts (schema layer)
- **Experiment 16**: lifecycle regression is a temporal coupling conflict
