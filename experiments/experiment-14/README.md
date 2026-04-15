# Experiment 14 — Git as RDF Conflict Detector: Confusion Matrix

## Key Question

When RDF graphs are split across team-owned files under Git, does Git's textual merge produce meaningful conflict signals for semantic (constraint-violating) conflicts — or does it miss them?

## Background

Experiments 1–13 used Flexo MMS (an RDF-native VCS) exclusively. This experiment asks: what happens if you use Git (a text-oriented VCS) instead? It establishes the **baseline motivation** for the RDF + Git mixed model by quantifying where Git succeeds and fails as a conflict detector for structured engineering data.

Reference: [BlockScience/ADCS-lifecycle-demo](https://github.com/BlockScience/ADCS-lifecycle-demo) — the satellite structural model adapted here.

## Model

The satellite model is split across files by **team ownership**, mirroring real multi-team engineering practice:

```
structural/
├── satellite.ttl    ← systems engineering (GeoSat, interface params)
├── adcs.ttl         ← ADCS team (components, power draw: 50W)
└── power.ttl        ← power team (solar arrays 2×180W, PDU 85%, battery)

requirements/
├── satellite.ttl    ← system-level requirements (SAT-REQ-*)
├── adcs.ttl         ← ADCS requirements (REQ-001 through REQ-004)
└── power.ttl        ← power requirements (REQ-P01, REQ-P02)

ontology/
├── rtm.ttl          ← RTM ontology (from ADCS-lifecycle-demo)
└── shapes.ttl       ← SHACL structural constraints

oracle/
├── c1-power-budget.rq         ← total draw ≤ available power
├── c2-power-generation.rq     ← declared available ≤ actual capacity
├── c3-requirement-allocation.rq ← traceability audit (informational)
└── c4-unallocated-requirements.rq ← subsystem reqs without satisfy links
```

**Power budget (ancestor state):**
- Available power: 306W (2 panels × 180W × 0.85 PDU efficiency)
- Total draw: 235W (ADCS 50W + Power 15W + Comms 120W + Thermal 40W + Structure 10W)
- Margin: 71W (23%)

## Scenarios

Four scenarios target each cell of the confusion matrix:

| # | Scenario | Branch A | Branch B | Files | Expected |
|---|----------|----------|----------|-------|----------|
| 1 | True Negative | ADCS tunes PD gains (Kp=1.5, Kd=15) | Power relaxes battery DOD (0.60→0.70) | Different | Git clean, valid |
| 2 | False Negative | ADCS upgrades wheels (draw 50→80W) | Power reduces panels (180→150W, avail 306→255W) | Different | Git clean, **INVALID** (265W > 255W) |
| 3 | True Positive | ADCS sets power draw to 55W | SysEng sets ADCS draw to 48W | Same line | Git conflict |
| 4 | False Positive | Reorder adcs.ttl blocks (seed 42) | Reorder adcs.ttl blocks (seed 43) | Same file, different text | Git conflict (content identical) |

## Results

### Confusion Matrix

|                | Sem. Valid | Sem. Invalid |
|----------------|:---------:|:------------:|
| **Git clean**   | 2 (TN) | 2 (FN) |
| **Git conflict**| 0 (FP) | 4 (TP) |

- **False negative rate: 33%** — Git misses semantic conflicts that span different files
- **False positive rate: 0%** — but only because conflicted files can't be validated (the reordered-serialization scenario *is* a false positive — Git conflicts on semantically identical content)

### Key Finding

**Git's conflict detection is file-scoped, not model-scoped.** When two teams modify different files that are coupled through shared constraints (power budget), Git merges cleanly even though the combined state violates the constraint. This is the false-negative case that motivates RDF-native validation: the power budget oracle query `c1-power-budget.rq` catches the 10W overrun (265W draw vs. 255W available) that Git cannot see.

Conversely, Git over-reports conflicts when Turtle serialization order changes — semantically identical graphs produce textual diffs that Git cannot distinguish from real edits. This is the false-positive case that motivates canonical serialization or RDF-aware diffing.

### Oracle Detail (Scenario 2)

```
c1-power-budget: totalDraw=265.0, available=255.0, violation=10.0
```

The ADCS team's wheel upgrade (+30W) and the Power team's panel reduction (available −51W) each individually stay within budget. Combined, they exceed it by 10W. Git sees no overlap — different teams, different files, clean merge.

## How to Run

```bash
cd experiments/experiment-14
python3 run.py
# Or capture log:
python3 run.py > run-output-$(date +%Y%m%d).log 2>&1
```

**Prerequisites:** Python 3.8+, `pip install rdflib pyshacl gitpython`

## Output Artifacts

```
output/
├── results.json              ← structured results
├── graphs/
│   ├── ancestor.ttl
│   ├── true-negative-*.ttl   ← merged states
│   └── false-negative-*.ttl
├── shacl/
│   └── *-report.txt          ← SHACL validation reports
├── repos/                    ← git repos (regenerated on each run, gitignored)
│   ├── true-negative/        inspect with: git -C output/repos/false-negative log --graph --all
│   ├── false-negative/
│   ├── true-positive/
│   └── false-positive/
└── git-log-*.txt             ← git log --graph for each scenario
```

## Connection to Other Experiments

This is "experiment zero" for the mixed model — it establishes *why* you need both Git (temporal) and RDF-native validation (spatial). Experiments 15–18 build on this finding:
- **Exp 15** extends the false-negative finding to ontology package composition
- **Exp 16** shows the same pattern with lifecycle gate violations
- **Exp 17** formalizes the dual-signal (Git + SHACL) classification
- **Exp 18** adds evidence freshness as a temporal-spatial property
