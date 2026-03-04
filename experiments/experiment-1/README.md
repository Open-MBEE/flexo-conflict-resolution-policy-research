# Experiment 1 — Satellite Scenario: Reproducibility Guide

This directory contains all artifacts needed to reproduce the satellite power subsystem conflict resolution experiment described in [Experiment 1 — Satellite Scenario](../../Experiment%201%20—%20Satellite%20Scenario.md).

## Prerequisites

- Docker runtime (Docker Desktop or [Colima](https://github.com/abiosoft/colima)) with **at least 12 GB** RAM allocated
- A clone of [flexo-mms-deployment](https://github.com/Open-MBEE/flexo-mms-deployment)
- `curl` and `python3` available on your PATH
- Default test credentials: `user01` / `password1`

### Setup from Zero

If you don't have Flexo running yet:

```bash
# 1. Install Colima (macOS) or ensure Docker Desktop has ≥12 GB RAM
brew install colima docker
colima start --cpu 4 --memory 12

# 2. Clone the deployment repo
git clone https://github.com/Open-MBEE/flexo-mms-deployment.git
cd flexo-mms-deployment/docker-compose

# 3. Start the Flexo stack
docker compose up -d

# 4. Wait for services (Fuseki needs time to initialize its 8 GB heap)
#    Watch for "Responding at http://0.0.0.0:8080" in:
docker compose logs -f layer1-service

# 5. Verify all 6 containers are running
docker compose ps
```

Expected containers: `openldap-server`, `quad-server`, `minio-server`, `auth-service`, `store-service`, `layer1-service`.

See [Local Deployment Setup](../../Local%20Deployment%20Setup.md) for detailed instructions.

## Directory Contents

```
experiment-1/
├── README.md                        ← this file
├── ancestor-model.ttl               ← ancestor state X (Turtle)
├── commit-u-upgrade-comms.ru        ← SPARQL UPDATE for commit u (branch-a)
├── commit-v-upgrade-thermal.ru      ← SPARQL UPDATE for commit v (branch-b)
├── oracle/
│   ├── c1-mass-budget.rq           ← C1: total mass ≤ mass budget
│   ├── c2-power-budget.rq          ← C2: total power ≤ power budget
│   ├── c3-bus-load.rq              ← C3: bus-connected power ≤ max load
│   ├── c4-nonneg-mass.rq           ← C4: mass ≥ 0 per subsystem
│   ├── c5-thermal-coupling.rq      ← C5: thermal capacity ≥ comm power × 0.3
│   ├── c6-owner-cardinality.rq     ← C6: max 1 owner per subsystem
│   └── name-multiplicity.rq        ← syntactic: detect multiple sat:name values
├── run.sh                           ← full experiment script
└── run-output-20260303.log          ← reference output from verified run
```

## Quick Start

```bash
# From this directory:
chmod +x run.sh
./run.sh
```

The script runs all steps end-to-end and prints results.

**Timing reference** (2026-03-03, Apple Silicon M3 Max, Colima 12 GB, QEMU emulation):

| Phase | Duration |
| --- | --- |
| Service readiness (Step 0) | ~15 s |
| Org + repo creation (Step 2) | ~27 s |
| Load + query ancestor (Steps 3–4) | ~8 s |
| Branch + commit + verify (Steps 5–7) | ~30 s |
| Cross-application + oracle (Steps 8–9) | ~23 s |
| **Total** | **~1 min 47 s** |

On a cold start (first `docker compose up`), Fuseki heap initialization adds 30–60 seconds and repo creation may take significantly longer (up to 10–15 minutes). Subsequent runs with warm services are much faster.

## Step-by-Step Walkthrough

All commands assume the Flexo instance is running on localhost with default ports (Layer 1 on 8080, Auth on 8082).

### Variables

```bash
BASE=http://localhost:8080
AUTH=http://localhost:8082
ORG=research
REPO=scenario-1
```

### Step 1: Authenticate

```bash
TOKEN=$(curl -s -u user01:password1 $AUTH/login \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

### Step 2: Create Org and Repo

```bash
# Create org (ignore 409 if it already exists)
curl -s -o /dev/null -w "%{http_code}" \
  -X PUT "$BASE/orgs/$ORG" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "research"@en .'

# Create repo
curl -s -o /dev/null -w "%{http_code}" \
  -X PUT "$BASE/orgs/$ORG/repos/$REPO" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "scenario-1"@en .'
```

### Step 3: Load Ancestor Model

Convert the Turtle file to a SPARQL UPDATE INSERT DATA and load it:

```bash
# Build INSERT DATA from Turtle file
TRIPLES=$(grep -v '^@prefix' ancestor-model.ttl | grep -v '^$')
UPDATE="PREFIX sat: <http://example.org/satellite/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
INSERT DATA {
$TRIPLES
}"

curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/master/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-update" \
  -d "$UPDATE"
```

### Step 4: Verify Ancestor Constraints

Run each oracle query against master:

```bash
for q in oracle/*.rq; do
  echo "=== $(basename $q) ==="
  curl -s -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/master/query" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/sparql-query" \
    -H "Accept: application/json" \
    --data-binary @"$q" | python3 -c "
import sys, json
data = json.load(sys.stdin)
for b in data['results']['bindings']:
    print('  ', {k: v['value'] for k, v in b.items()})
if not data['results']['bindings']:
    print('  (no results — constraint satisfied)')
"
done
```

All constraints should show negative violation values (slack) or empty results (satisfied).

### Step 5: Create Branches

```bash
# branch-a (for commit u)
curl -s -o /dev/null -w "branch-a: %{http_code}\n" \
  -X PUT "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "branch-a"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./master> .'

# branch-b (for commit v)
curl -s -o /dev/null -w "branch-b: %{http_code}\n" \
  -X PUT "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "branch-b"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./master> .'
```

### Step 6: Apply Commits

```bash
# Commit u on branch-a
curl -s -o /dev/null -w "commit u: %{http_code}\n" \
  -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/branch-a/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-update" \
  --data-binary @commit-u-upgrade-comms.ru

# Commit v on branch-b
curl -s -o /dev/null -w "commit v: %{http_code}\n" \
  -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/branch-b/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-update" \
  --data-binary @commit-v-upgrade-thermal.ru
```

### Step 7: Verify Individual Validity

Run oracle queries against each branch (same loop as Step 4 but targeting `branch-a` and `branch-b`). All constraints should pass on both branches independently.

### Step 8: Construct Cross-Application States

```bash
# branch-uv = f(f(X,u),v) — branch from branch-a, apply v
curl -s -o /dev/null -w "branch-uv: %{http_code}\n" \
  -X PUT "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "branch-uv"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-a> .'

curl -s -o /dev/null -w "apply v to branch-uv: %{http_code}\n" \
  -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/branch-uv/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-update" \
  --data-binary @commit-v-upgrade-thermal.ru

# branch-vu = f(f(X,v),u) — branch from branch-b, apply u
curl -s -o /dev/null -w "branch-vu: %{http_code}\n" \
  -X PUT "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> <http://purl.org/dc/terms/title> "branch-vu"@en .
<> <https://mms.openmbee.org/rdf/ontology/ref> <./branch-b> .'

curl -s -o /dev/null -w "apply u to branch-vu: %{http_code}\n" \
  -X POST "$BASE/orgs/$ORG/repos/$REPO/branches/branch-vu/update" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/sparql-update" \
  --data-binary @commit-u-upgrade-comms.ru
```

### Step 9: Evaluate Oracle on Cross-Application States

Run oracle queries against `branch-uv` and `branch-vu`.

**Expected results (all stages):**

| Stage | C1 mass | C2 power | C3 bus | C4 local | C5 coupling | C6 owner | name |
| --- | --- | --- | --- | --- | --- | --- | --- |
| master | -50 | -25 | -25 | satisfied | -10.5 | satisfied | satisfied |
| branch-a | -35 | -10 | -10 | satisfied | -6.0 | satisfied | satisfied |
| branch-b | -30 | -10 | -10 | satisfied | -10.5 | satisfied | satisfied |
| branch-uv | -15 | **+5** | **+5** | satisfied | -6.0 | **2 owners** | **2 names** |
| branch-vu | -15 | **+5** | **+5** | satisfied | -6.0 | **2 owners** | **2 names** |

Both cross-application states produce identical results (commutativity confirmed).

## Expected Conflict Summary

| Conflict | Level | Description |
| --- | --- | --- |
| `sat:name` dual values | Syntactic | `"HighBandwidthComm"` and `"CommunicationsSubsystem"` |
| C6 owner cardinality | Structural | `TeamAlpha` and `TeamBeta` both own CommSubsystem |
| C2 power budget | Semantic | Combined power 55 > budget 50 |
| C3 bus load | Semantic | Combined power 55 > max load 50 |

## Troubleshooting

### Service startup

The script waits for Layer 1 and the Auth service to become ready before proceeding (Step 0). On Apple Silicon under QEMU emulation, Fuseki may take 30-60 seconds to initialize its 8 GB heap. If you see "waiting..." messages, this is normal.

If the script times out after 180 seconds, check:

```bash
# Are all containers running?
docker compose ps

# Check Fuseki logs for OOM or heap errors
docker compose logs quad-server --tail 20
```

Fuseki requires at least 8 GB heap. If your Colima VM has less than 12 GB total memory, Fuseki will crash with `os::commit_memory failed`. Restart Colima with more memory:

```bash
colima stop && colima start --cpu 4 --memory 12
```

### Stale state from previous runs

The script accepts HTTP 409 (Conflict) on org and repo creation, so re-running against an existing `scenario-1` repo will not fail at Step 2. However, the ancestor model and branch data will be additive — triples from the previous run remain. For clean results, **you must restart Flexo between runs**:

```bash
cd flexo-mms-deployment/docker-compose
docker compose down && docker compose up -d
```

### Fuseki transaction locks

If the script is killed mid-request (Ctrl-C, OOM, timeout), Fuseki may hold a write transaction lock. Subsequent write requests will hang indefinitely. The only fix is a full restart:

```bash
cd flexo-mms-deployment/docker-compose
docker compose down && docker compose up -d
```

This is a known Fuseki behavior, not a bug in the script.

### Token expiry

JWT tokens expire after a period of inactivity. The script refreshes the token before Steps 3, 7, and 9. If you still encounter 401 errors, re-run the script from a clean Flexo instance — it will re-authenticate at Step 1.

### SPARQL query parse errors (curl `-d` vs `--data-binary`)

If oracle queries fail with `QueryParseException: Encountered "<EOF>"`, the likely cause is using `curl -d @file` instead of `curl --data-binary @file`. The `-d` flag strips newlines from file content, which causes `#` comment lines in the `.rq` files to swallow the entire query (SPARQL comments extend to end of line, so without a newline the comment never terminates). Always use `--data-binary @file` when sending SPARQL from files.

## Notes

- **PUT graph vs SPARQL UPDATE**: Loading model data via `PUT .../branches/master/graph` with inline Turtle may return 200 but leave the model empty in queries. Use `POST .../update` with `INSERT DATA` instead.
- **Apple Silicon / QEMU**: All Flexo images are `linux/amd64` only and run under QEMU emulation on ARM Macs. Operations are 3-10x slower than native. Individual API calls may take 5-30 seconds.
- **Cold vs warm starts**: The first run after `docker compose up` is significantly slower because Fuseki must allocate its 8 GB Java heap under emulation. Subsequent runs with warm services complete in under 2 minutes.
