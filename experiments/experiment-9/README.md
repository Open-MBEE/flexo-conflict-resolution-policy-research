# Experiment 9 — Satellite Scenario on Remote Layer 1 SPARQL API

## What is being tested

Does the **remote** Layer 1 SPARQL API at `try-layer1.starforge.app` produce identical results to the **local** Flexo instance (Experiment 1)?

This is the first experiment running SPARQL queries against a hosted Layer 1 endpoint — all previous SPARQL experiments (1, 3, 4) ran against `localhost:8080`.

## How

Same satellite conflict scenario as Experiment 1. All data files and oracle queries are imported from Experiment 1 via symlinks.

## Imported Files (from experiment-1/)

| File | Purpose |
| --- | --- |
| `ancestor-model.ttl` | Satellite system ancestor state (4 elements) |
| `commit-u-upgrade-comms.ru` | SPARQL UPDATE: Team Alpha upgrades comms |
| `commit-v-upgrade-thermal.ru` | SPARQL UPDATE: Team Beta upgrades thermal |
| `oracle/*.rq` | 7 constraint queries (C1–C6 + name multiplicity) |

These are identical to Experiment 1. Only the run script differs (remote endpoint, pre-issued token, no service polling).

## Prerequisites

- `curl` and `python3` on PATH
- `FLEXO_TOKEN` environment variable set to the pre-issued Bearer token

## Quick Start

```bash
export FLEXO_TOKEN="eyJhbGci..."
./run.sh
```

## Expected Results

Identical to Experiment 1. See [Experiment 1 README](../experiment-1/README.md) for the full expected results table.

## Run Status

**2026-03-18:** Initial run succeeded during interactive session (results matched Experiment 1 exactly), but output was not captured to a log file at that time. Subsequent re-runs to capture logs failed — `try-layer1.starforge.app` became unresponsive (HTTP 504 on write operations, full timeout on reads). The service needs to be restarted or investigated before logs can be captured. See `run-output-20260318.log` for the failure trace.
