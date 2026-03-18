# Experiment 2 — Satellite Scenario: Remote Flexo (SysML v2 REST API)

This experiment runs the same satellite power subsystem conflict resolution scenario as [Experiment 1](../experiment-1/README.md), but against the **remote** OpenMBEE Flexo SysML v2 service instead of a local Docker deployment.

## Why This Experiment Exists

Experiment 1 uses the Flexo MMS **Layer 1 SPARQL API** — a low-level interface that exposes raw RDF triples, SPARQL UPDATE for writes, and SPARQL SELECT for queries. This works well locally but is not exposed by the remote OpenMBEE service.

The remote service at `https://experimental.starforge.app/` exposes only the **SysML v2 REST API** — a higher-level interface with Projects, Branches, Commits, and Elements as JSON resources. This is the standard API that tools and clients are expected to use.

Experiment 2 rewrites the scenario to use this REST API, translating:

| Experiment 1 (SPARQL) | Experiment 2 (REST API) |
| --- | --- |
| `PUT /orgs/.../repos/...` | `POST /projects` |
| `PUT /orgs/.../repos/.../branches/...` | `POST /projects/{id}/branches` |
| `POST .../branches/.../update` (SPARQL UPDATE) | `POST /projects/{id}/commits?branchId={bid}` (JSON) |
| `POST .../branches/.../query` (SPARQL SELECT) | `GET /projects/{id}/commits/{cid}/elements` + Python |
| Oracle: 7 SPARQL `.rq` files | Oracle: 7 Python functions in `oracle.py` |
| Model: `.ttl` + `.ru` files | Model: Python dicts in `model.py` |

## What We Learn by Comparing Experiments 1 and 2

1. **Reproducibility across API layers** — The same conflicts emerge whether we use low-level SPARQL or the SysML v2 REST API, proving conflicts are inherent to the model, not an artifact of the API.
2. **API compatibility** — The SysML v2 REST API supports the branching/commit/element patterns needed for conflict detection research.
3. **Accessibility** — No Docker, Colima, 12 GB RAM, or QEMU emulation required. Anyone with Python 3 and an API token can reproduce the experiment.
4. **Performance baseline** — Comparing execution times between local QEMU-emulated stack and remote hosted service.

## Prerequisites

- Python 3.8+
- `requests` library (`pip install requests`)
- A valid API token for the remote Flexo service

No Docker, Colima, or local Flexo deployment is required.

## Remote Service

| Property | Value |
| --- | --- |
| Endpoint | `https://experimental.starforge.app/` |
| Auth | Bearer token (pre-issued) |
| API | SysML v2 REST (Projects, Branches, Commits, Elements) |
| Architecture | [Flexo-MMS](https://openmbee.atlassian.net/wiki/spaces/OPENMBEE/pages/320765953/Flexo-MMS+Architecture) |
| Python Client | [sysmlv2-python-client](https://github.com/Open-MBEE/sysmlv2-python-client) (not required, experiment uses raw `requests`) |

**Important:** This service is experimental and provided for testing purposes only. No guarantees of availability, performance, or uptime. Data may be deleted at any time. Do not upload sensitive or proprietary data.

## Directory Contents

```
experiment-2/
├── README.md              ← this file
├── run.py                 ← main experiment script
├── model.py               ← satellite model definitions (ancestor + commits)
├── oracle.py              ← 7 constraint evaluation functions
└── requirements.txt       ← Python dependencies
```

### File Mapping to Experiment 1

| Experiment 1 | Experiment 2 | Purpose |
| --- | --- | --- |
| `run.sh` (bash/curl) | `run.py` (Python/requests) | Orchestration |
| `ancestor-model.ttl` | `model.py: ANCESTOR_ELEMENTS` | Initial satellite state |
| `commit-u-upgrade-comms.ru` | `model.py: COMMIT_U_CHANGES` | Team Alpha's changes |
| `commit-v-upgrade-thermal.ru` | `model.py: COMMIT_V_CHANGES` | Team Beta's changes |
| `oracle/c1-mass-budget.rq` | `oracle.py: c1_mass_budget()` | Mass budget constraint |
| `oracle/c2-power-budget.rq` | `oracle.py: c2_power_budget()` | Power budget constraint |
| `oracle/c3-bus-load.rq` | `oracle.py: c3_bus_load()` | Bus load constraint |
| `oracle/c4-nonneg-mass.rq` | `oracle.py: c4_nonneg_mass()` | Non-negative mass constraint |
| `oracle/c5-thermal-coupling.rq` | `oracle.py: c5_thermal_coupling()` | Thermal coupling constraint |
| `oracle/c6-owner-cardinality.rq` | `oracle.py: c6_owner_cardinality()` | Owner cardinality constraint |
| `oracle/name-multiplicity.rq` | `oracle.py: name_multiplicity()` | Name multiplicity constraint |

## Quick Start

```bash
# Install dependency
pip install requests

# Set your API token
export FLEXO_BEARER_TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# Run the experiment
python3 run.py

# Or run with cleanup (deletes the project from the remote service afterward)
python3 run.py --cleanup
```

## Expected Results

Results should be identical to Experiment 1:

| Stage | C1 mass | C2 power | C3 bus | C4 local | C5 coupling | C6 owner | name |
| --- | --- | --- | --- | --- | --- | --- | --- |
| master | -50 | -25 | -25 | satisfied | -10.5 | satisfied | satisfied |
| branch-a | -35 | -10 | -10 | satisfied | -6.0 | satisfied | satisfied |
| branch-b | -30 | -10 | -10 | satisfied | -10.5 | satisfied | satisfied |
| branch-uv | -15 | **+5** | **+5** | satisfied | -6.0 | **2 owners** | **2 names** |
| branch-vu | -15 | **+5** | **+5** | satisfied | -6.0 | **2 owners** | **2 names** |

Both cross-application states should produce identical results (commutativity confirmed).

## Expected Conflict Summary

| Conflict | Level | Description |
| --- | --- | --- |
| `sat:name` dual values | Syntactic | `"HighBandwidthComm"` and `"CommunicationsSubsystem"` |
| C6 owner cardinality | Structural | `TeamAlpha` and `TeamBeta` both own CommSubsystem |
| C2 power budget | Semantic | Combined power 55 > budget 50 |
| C3 bus load | Semantic | Combined power 55 > max load 50 |

## Key Design Decisions

### Why Python instead of bash/curl?

The remote service has no SPARQL endpoint. Constraint evaluation (the "oracle") must happen client-side. Python makes this natural and readable; bash + jq would be fragile.

### Why not use the sysmlv2-python-client library?

The API calls are simple enough (6 endpoints) that raw `requests` keeps the experiment self-contained with zero non-standard dependencies. The library is noted here for reference.

### How are cross-application states constructed?

In Experiment 1, SPARQL UPDATE operations (DELETE/INSERT) are applied server-side, and RDF naturally accumulates multiple triples (e.g., two `sat:owner` values for the same subject). The SysML v2 REST API replaces entire elements on commit, so Experiment 2 computes the merged element state client-side in `apply_changes_to_elements()`, explicitly handling owner list merging and name conflicts.

## Troubleshooting

### Cannot reach remote service

If Step 1 fails, check your internet connection and whether `https://experimental.starforge.app/` is accessible in a browser. The service is experimental with no uptime guarantees.

### Authentication errors

Verify `FLEXO_BEARER_TOKEN` is set correctly. The token is a JWT — decode it at [jwt.io](https://jwt.io) to check the `exp` (expiration) field.

### Stale state from previous runs

Each run creates a new project with a unique ID, so previous runs don't interfere. Use `--cleanup` to delete projects after the experiment, or delete them manually via the API.
