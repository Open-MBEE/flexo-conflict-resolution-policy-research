# Experiment 11 — MTG-KC Full Schema on Remote Layer 1 SPARQL API

## What is being tested

Does the remote Layer 1 SPARQL API produce identical results to the local Flexo instance (Experiment 4) when **OWL ontology and SHACL shapes** are loaded alongside instance data?

## How

Same scenario as Experiment 4. Loads ontology.ttl + shapes.ttl + instance.ttl, then runs the structural conflict (remove BG vs enrich BG) with schema-aware oracle queries (C5 type consistency, C6 shape targets).

## Imported Files (from experiment-4/)

| File | Purpose |
| --- | --- |
| `ancestor-model.ttl` | MTG-KC instance (25 simplicial elements) |
| `ontology.ttl` | OWL ontology (class hierarchy, properties) |
| `shapes.ttl` | SHACL shapes (topological + vocabulary constraints) |
| `commit-u-remove-bg.ru` | SPARQL UPDATE: delete BG + dependent faces |
| `commit-v-enrich-bg.ru` | SPARQL UPDATE: enrich BG + BRG |
| `oracle/*.rq` | 6 constraint queries (C1–C6) |

## Prerequisites

- `curl` and `python3` on PATH
- `FLEXO_TOKEN` environment variable

## Quick Start

```bash
export FLEXO_TOKEN="eyJhbGci..."
./run.sh
```

## Expected Results

Identical to Experiment 4. See [Experiment 4 README](../experiment-4/README.md) for the full results including SHACL shape target coverage.

## Run Status

**2026-03-18 (run 1):** Succeeded during interactive session, results matched Experiment 4 exactly. Output not captured to log.

**2026-03-18 (run 2):** Re-run to capture logs failed — `try-layer1.starforge.app` became unresponsive (HTTP 504).

**2026-03-18 (run 3):** Service recovered. Full successful run captured in `run-output-20260318.log`. Results identical to Experiment 4 (same C5/C6 schema-aware results, same shape target counts).
