# Experiment 10 — MTG-KC Instance Only on Remote Layer 1 SPARQL API

## What is being tested

Does the remote Layer 1 SPARQL API produce identical results to the local Flexo instance (Experiment 3) for **non-SysML RDF data** (the MTG Knowledge Complex)?

## How

Same structural conflict scenario as Experiment 3 (remove BG edge vs enrich BG). All data files and oracle queries are imported from Experiment 3 via symlinks.

## Imported Files (from experiment-3/)

| File | Purpose |
| --- | --- |
| `ancestor-model.ttl` | MTG-KC instance (25 simplicial elements) |
| `commit-u-remove-bg.ru` | SPARQL UPDATE: delete BG + dependent faces |
| `commit-v-enrich-bg.ru` | SPARQL UPDATE: enrich BG + BRG |
| `oracle/*.rq` | 4 constraint queries (C1–C4) |

## Prerequisites

- `curl` and `python3` on PATH
- `FLEXO_TOKEN` environment variable

## Quick Start

```bash
export FLEXO_TOKEN="eyJhbGci..."
./run.sh
```

## Expected Results

Identical to Experiment 3. See [Experiment 3 README](../experiment-3/README.md) for the full results including the non-commutativity finding.
