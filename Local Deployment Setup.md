# Local Deployment Setup

How to stand up a local Flexo MMS instance for conflict resolution experiments using the [flexo-mms-deployment](https://github.com/Open-MBEE/flexo-mms-deployment) Docker Compose stack.

## Prerequisites

- **Docker** runtime (Docker Desktop or [Colima](https://github.com/abiosoft/colima))
- **Memory**: Allocate at least 12 GB RAM to the Docker VM. The [[Apache Jena Fuseki]] quadstore alone is configured with an 8 GB heap (`-Xmx8192m`). On Colima: `colima start --cpu 4 --memory 12`
- **Free ports**: 8080 (Layer 1), 8082 (Auth), 8081 (Store), 3030 (Fuseki), 9000 (MinIO), 1389 (LDAP)

## Services

The Docker Compose stack starts six containers on a single bridge network (`flexo-mms-test-network`):

| Service | Port | Purpose |
|---------|------|---------|
| OpenLDAP | 1389 | User authentication backend — creates default test users |
| [[Apache Jena Fuseki]] | 3030 | [[Quadstore]] (Layer 0) — stores all RDF graphs and system metadata |
| MinIO | 9000 | S3-compatible object storage for large model uploads |
| Auth Service | 8082 | LDAP-to-JWT bridge — issues bearer tokens for API calls |
| Store Service | 8081 | Artifact storage layer backed by MinIO |
| Layer 1 Service | 8080 | Core MMS API — [[SPARQL]], [[Graph Store Protocol]], CRUD |

## Startup

Clone the deployment repo (or pull if you already have it):

```bash
git clone https://github.com/Open-MBEE/flexo-mms-deployment.git
cd flexo-mms-deployment
git pull
```

Then bring up the services:

```bash
cd docker-compose
docker compose up -d
```

Wait for Layer 1 to log `Responding at http://0.0.0.0:8080` (check with `docker logs layer1-service`).

## Bootstrap Workflow

### 1. Authenticate

```bash
TOKEN=$(curl -s -u user01:password1 http://localhost:8082/login \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])")
```

Default test credentials: `user01` / `password1` (admin), `user02` / `password2`.

### 2. Create an Org and Repo

```bash
curl -X PUT http://localhost:8080/orgs/research \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> dct:title "research"@en .'

curl -X PUT http://localhost:8080/orgs/research/repos/conflict-experiments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  -d '<> dct:title "conflict-experiments"@en .'
```

Creating a repo automatically produces a `master` branch and an initial (empty) commit.

### 3. Load Model Data

```bash
curl -X PUT http://localhost:8080/orgs/research/repos/conflict-experiments/branches/master/graph \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: text/turtle" \
  --data-binary @gnis-hawaii.ttl
```

The `gnis-hawaii.ttl` sample dataset ships in the `docker-compose/` directory. For experiments, any valid Turtle file can be loaded this way — the `PUT .../graph` endpoint replaces the entire model graph on the branch.

### 4. Branch, Update, Query

```bash
# Create a branch from master
curl -X PUT .../branches/experiment-1 \
  -H "Content-Type: text/turtle" \
  -d '<> dct:title "experiment-1"@en .
<> mms:ref <./master> .'

# SPARQL Update on a branch
curl -X POST .../branches/experiment-1/update \
  -H "Content-Type: application/sparql-update" \
  -d 'PREFIX ex: <http://example.org/> INSERT DATA { ex:test ex:prop "value" . }'

# SPARQL Query on a branch
curl -X POST .../branches/experiment-1/query \
  -H "Content-Type: application/sparql-query" \
  -d 'SELECT * { ?s ?p ?o } LIMIT 10'
```

## API Quick Reference

| Operation | Method | Endpoint Pattern |
|-----------|--------|-----------------|
| Login | `GET` | `/login` (port 8082, Basic Auth) |
| Create org | `PUT` | `/orgs/{orgId}` |
| Create repo | `PUT` | `/orgs/{orgId}/repos/{repoId}` |
| Load model | `PUT` | `.../branches/{branchId}/graph` |
| Get model | `GET` | `.../branches/{branchId}/graph` |
| SPARQL Query | `POST` | `.../branches/{branchId}/query` |
| SPARQL Update | `POST` | `.../branches/{branchId}/update` |
| Create branch | `PUT` | `.../branches/{branchId}` |
| Repo metadata query | `POST` | `.../repos/{repoId}/query` |
| Create policy | `PUT` | `/policies/{policyId}` |

Full spec: [Layer 1 OpenAPI](https://www.openmbee.org/flexo-mms-layer1-openapi/)

## Cluster Initialization

The file `mount/cluster.trig` is automatically loaded into Fuseki at startup via the Fuseki `--file` flag. This TriG file bootstraps:

- **System users**: `root`, `admin`, `anon`, plus LDAP-mapped `user01` and `user02`
- **Groups**: `SuperAdmins`, `group01` (LDAP group)
- **Access control policies**: `DefaultSuperAdmins` grants full admin roles to `user01` and `group01`
- **Schema**: Flexo's ontology classes (`Org`, `Repo`, `Branch`, `Commit`, `Lock`, `Ref`, etc.) and permission/role hierarchy

This means the quadstore contains *both* user model data and Flexo system state in different named graphs. The [[Quadstore]] note describes the named graph categories (System, Metadata, Model).

## Jupyter Integration

Run a notebook on the Docker network for programmatic experiments:

```bash
docker run -p 8888:8888 --network=flexo-mms-test-network jupyter/scipy-notebook:latest
```

From inside the notebook, use internal hostnames:

```python
import requests
from requests.auth import HTTPBasicAuth

resp = requests.get("http://auth-service:8080/login",
                     auth=HTTPBasicAuth('user01', 'password1'))
token = resp.json()['token']
headers = {"Authorization": f"Bearer {token}"}

sparql = "SELECT * { ?s ?p ?o } LIMIT 10"
resp = requests.post(
    "http://layer1-service:8080/orgs/research/repos/conflict-experiments/branches/master/query",
    headers={**headers, "Content-Type": "application/sparql-query"},
    data=sparql)
print(resp.json())
```

## Gotchas and Learnings

- **Docker VM memory**: Fuseki's 8 GB heap requires at least 12 GB allocated to the Docker VM. With the default 2 GB on Colima, Fuseki exits immediately with `os::commit_memory failed`. On Colima, set memory at startup: `colima start --memory 12`.
- **Port conflicts**: The default ports (8080–8082) conflict with other local services (e.g. koi-net nodes). Either stop conflicting services or remap ports in `docker-compose.yml`.
- **Auth service platform warning**: The auth service image is `linux/amd64` only. On Apple Silicon it runs under QEMU emulation, which works but logs a platform mismatch warning.
- **Fuseki UI**: Available at `http://localhost:3030` for direct SPARQL queries against the quadstore — useful for inspecting system graphs alongside model data.
- **Shutdown**: `docker compose down` from the `docker-compose/` directory. Data does not persist across restarts unless Docker volumes are configured.

## Relevance to Conflict Resolution Research

This local instance provides the experimental substrate for the work formalized in [[Conflict Resolution Problem Statement]]:

- **Branching** creates divergent model states ($X_A$, $X_B$) from a common ancestor
- **SPARQL Update** patches are the *commits* ($u$, $v$) — descriptions of intended change
- **Querying** both branches reveals the divergence that the resolution policy must reconcile
- The [[Merge]] endpoint (once implemented) is where the resolution function $w^* = \arg\min \mathcal{L}(w)$ will execute
- The repo metadata query shows the full commit DAG — the structure the [[Predicate Compliance Oracle]] evaluates against

Current Flexo (v0.2.2) does not yet implement three-way merge or conflict detection. Experiments at this stage focus on constructing controlled divergence scenarios and validating the constraint evaluation pipeline that will inform the merge policy.

### Experiments Run on This Instance

- [[Experiment 1 — Satellite Scenario]] — satellite power subsystem model demonstrating syntactic, structural, and semantic conflicts via cross-application analysis

---
← [[Flexo Organization Level]] · [[Apache Jena Fuseki]] · [[Flexo MMS]]
