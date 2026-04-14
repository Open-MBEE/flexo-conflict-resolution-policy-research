# Cross-Experiment Analysis

Scripts for synthesizing findings across Experiments 14–18.

## Scripts

- **`analyze.py`** — Produces comparison tables (conflict detection, signal effectiveness, temporal-vs-spatial matrix). Outputs to `tables/`.
- **`report.py`** — Generates `report.md` with executive summary, per-experiment findings, cross-experiment synthesis, and open questions.

## How to Run

```bash
cd experiments
uv run python analysis/analyze.py
uv run python analysis/report.py
```

Both scripts handle missing `results.json` files gracefully — run them after any subset of experiments.

## Output

```
tables/
├── conflict-detection.md    ← what each signal detected per scenario
├── conflict-detection.csv   ← same, machine-readable
├── signal-effectiveness.md  ← catch rate / miss rate per signal type
├── signal-effectiveness.csv
└── temporal-vs-spatial.md   ← core thesis table

report.md                    ← full synthesis report
```
