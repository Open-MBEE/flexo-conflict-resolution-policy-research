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

## Run Status

**2026-03-18:** Initial run succeeded during interactive session (results matched Experiment 3 exactly — same non-commutativity, same orphaned properties on branch-uv), but output was not captured to a log file at that time. Subsequent re-runs to capture logs failed — `try-layer1.starforge.app` became unresponsive (HTTP 504 on write operations, full timeout on reads). The service needs to be restarted or investigated before logs can be captured. See `run-output-20260318.log` for the failure trace.
