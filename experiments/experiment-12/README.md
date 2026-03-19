# Experiment 12 — Three-Layer Flexo Service Architecture

## Motivation

Experiments 1–11 demonstrated that Flexo can detect merge conflicts across API layers and ontology families. A recurring implicit pattern emerged: the quadstore, the ontology, and the constraint-checking logic each play distinct architectural roles. This experiment makes the pattern **explicit**.

The goal is **architectural clarity** — not solving conflicts. We've already shown that independently valid commits can produce invalid merged states (Experiments 3–4). What this experiment adds is a clear demonstration of *where each concern lives* and how they compose.

## The Three-Layer Pattern

```
┌─────────────────────────────────────────────┐
│  Layer 3 — VERIFICATION                     │
│  Constraint checking as a service.           │
│  SHACL validation + SPARQL oracle.           │
│  Can optionally gate commits.                │
├─────────────────────────────────────────────┤
│  Layer 2 — SEMANTIC (Ontology Packages)      │
│  Modular, composable interpretation layer.   │
│  Core ontology + domain extensions.          │
│  Like package management — import what       │
│  you need, compose without conflict.         │
├─────────────────────────────────────────────┤
│  Layer 1 — SYNTACTIC (Quadstore)             │
│  Accepts any valid RDF.                      │
│  Indifferent to interpretation.              │
│  Flexo Layer 1 + Apache Jena Fuseki.         │
└─────────────────────────────────────────────┘
```

**Layer 1** stores triples. It doesn't know what a `Complex` or `Edge` means — it just ensures valid RDF. Flexo's branching, committing, and diffing all operate here.

**Layer 2** provides the vocabulary and structure for interpreting the data. Ontology packages are modular: a core package defines abstract types, and domain packages extend them. This is analogous to package management — you import what you need, and packages compose without conflict as long as their namespaces don't collide.

**Layer 3** checks whether the data satisfies the constraints declared by the ontology packages. This is where SHACL shape validation and SPARQL constraint queries execute. In a production architecture, this service could **gate commits** — rejecting changes that would put a branch into a non-compliant state. Currently implemented client-side (pyshacl + rdflib); a hosted verification service would live here.

## KC ↔ SysML v2 Correspondence

The Knowledge Complex stack used in this experiment mirrors the SysML v2 layering at smaller scale. This makes the architectural pattern legible in a single experiment run:

| KC Stack (this experiment) | SysML v2 Stack (future experiment) |
| --- | --- |
| Quadstore (Fuseki) — valid RDF | Quadstore (Fuseki) — valid RDF |
| KC Core ontology (Element, Vertex, Edge, Face, Complex, boundedBy) | KerML (core modeling abstractions: features, types, relationships) |
| MTG Domain ontology (Color, ColorPair, ColorTriple, guild, theme...) | SysML v2 domain/discipline extensions (mechanical, electrical, thermal...) |
| SHACL shapes (boundary-closure, cardinality, triangle) | KerML/SysML v2 compiler checks + constraint verification services |
| Client-side pyshacl + SPARQL oracle | Hosted verification service (when available) |

The KC stack comprises 6 classes, 2 object properties, ~15 datatype properties, and 6 SHACL shapes. When KerML and SysML v2 compiler/verification services become available, a parallel experiment should demonstrate the same three-layer pattern at full SysML scale.

## Ontology Package Structure

```
ontology/
├── kc-core/                  ← Package 1: abstract topological backbone
│   ├── ontology.ttl          ← 5 classes, 2 properties, OWL restrictions
│   └── shapes.ttl            ← 3 SHACL shapes (ComplexShape, EdgeShape, FaceShape)
└── mtg-domain/               ← Package 2: domain extension (depends on kc-core)
    ├── ontology.ttl          ← 3 classes (subClassOf kc:), 14 domain properties
    └── shapes.ttl            ← 3 SHACL shapes (ColorShape, ColorPairShape, ColorTripleShape)
```

Each package is self-contained with its own ontology and shapes. The domain package declares `@prefix kc:` and `owl:imports <https://example.org/kc>` to express its dependency on the core. When loaded into the quadstore, the URIs resolve identically regardless of which file they came from — the file-level split makes the package boundary visible to humans and tooling.

## What This Experiment Demonstrates

1. **Layer 1 accepts everything**: The quadstore stores instance data, ontology triples, and SHACL shapes identically — they're all just RDF. It also stores cross-application states that violate constraints, without complaint.

2. **Layer 2 is modular**: The ontology is split into composable packages loaded sequentially. The core package provides the topological backbone; the domain package extends it with MTG-specific types and properties.

3. **Layer 3 detects what Layer 1 cannot**: The client-side verification service fetches triples from Flexo via SPARQL CONSTRUCT, loads the ontology packages, runs SHACL validation and oracle queries, and reports pass/fail. It successfully validates the ancestor and individual commits (PASS), then catches the invalid merged states (FAIL).

4. **The conflict scenario is the proof**: No synthetic bad data is needed. The cross-application states are syntactically valid RDF that Layer 1 happily stores — but they fail at Layer 3. The merge conflicts naturally demonstrate why all three layers are necessary.

## Prerequisites

- Running local Flexo MMS instance (see `Local Deployment Setup.md`)
  - Docker/Colima with 12+ GB RAM
  - All 6 containers running (layer1-service, auth-service, store-service, quad-server, minio-server, openldap-server)
- Python 3.8+ with `rdflib` and `pyshacl`:
  ```bash
  pip install -r requirements.txt
  ```
- `curl` on PATH

## Running

```bash
# For clean state, restart the Flexo stack first:
cd ~/Documents/GitHub/flexo-mms-deployment/docker-compose
docker compose down && docker compose up -d
# Wait ~60s for Fuseki to initialize

# Run the experiment:
cd experiments/experiment-12
./run.sh
```

Expected runtime: 3–7 minutes on Apple Silicon (QEMU emulation).

## Expected Results

| Branch | Layer 1 | Layer 3 (SHACL) | Layer 3 (Oracle) | Notes |
| --- | --- | --- | --- | --- |
| master (ancestor) | Accepted | PASS | PASS | All 25 elements valid |
| branch-a (commit u) | Accepted | PASS | PASS | BG + dependent faces removed |
| branch-b (commit v) | Accepted | PASS | PASS | BG/BRG enriched with properties |
| branch-uv (u then v) | Accepted | **FAIL** | **FAIL** | Orphaned properties on deleted elements |
| branch-vu (v then u) | Accepted | **FAIL** | **FAIL** | Different violations (non-commutativity) |

The key finding: Layer 1 accepted all five states. Only Layer 3 can distinguish valid from invalid. And the two cross-application orderings produce *different* violations — the conflict is non-commutative, meaning application order matters for the residual data state.

## File Manifest

| File | Layer | Description |
| --- | --- | --- |
| `run.sh` | Orchestrator | Main script — drives all three layers |
| `verify.py` | Layer 3 | Client-side verification service (pyshacl + rdflib SPARQL) |
| `ontology/kc-core/ontology.ttl` | Layer 2 | KC core OWL ontology |
| `ontology/kc-core/shapes.ttl` | Layer 2 | KC core SHACL shapes |
| `ontology/mtg-domain/ontology.ttl` | Layer 2 | MTG domain OWL extension |
| `ontology/mtg-domain/shapes.ttl` | Layer 2 | MTG domain SHACL shapes |
| `instance/ancestor-model.ttl` | Layer 1 | Pure instance data (25 MTG elements) |
| `commits/commit-u-remove-bg.ru` | Layer 1 | SPARQL UPDATE: remove BG + dependent faces |
| `commits/commit-v-enrich-bg.ru` | Layer 1 | SPARQL UPDATE: enrich BG/BRG properties |
| `oracle/*.rq` | Layer 3 | SPARQL constraint queries (C1–C6) |
| `requirements.txt` | — | Python dependencies |
