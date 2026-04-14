# Experiment 12 — Three Service Concerns for Flexo

## Motivation

Experiments 1–11 demonstrated that Flexo can detect merge conflicts across API layers and ontology families. A recurring implicit pattern emerged: storage, interpretation, and constraint-checking each play distinct roles that should be understood as separate service concerns. This experiment makes that separation **explicit**.

The goal is **architectural clarity** — not solving conflicts. We've already shown that independently valid commits can produce invalid merged states (Experiments 3–4). What this experiment adds is a clear demonstration of *where each concern lives*, what function each serves, and how they compose.

## Three Service Concerns

Flexo MMS defines four architectural layers (Layer 0–3: Quadstore, Layer 1 service, SysML v2 API, Client) that describe how data flows through the system. Orthogonal to those layers, we identify three **service concerns** — distinct functions that a complete model management platform must provide. Each concern may span one or more architectural layers:

```
┌──────────────────────────────────────────────────┐
│  VERIFICATION                                     │
│  Constraint compliance as a service.              │
│  Checks model state against declared rules.       │
│  Can optionally gate commits.                     │
├──────────────────────────────────────────────────┤
│  SCHEMA                                           │
│  Ontology packages — modular, composable.         │
│  Core ontology + domain extensions.               │
│  Defines what the data means and what             │
│  well-formedness requires.                        │
├──────────────────────────────────────────────────┤
│  STORAGE                                          │
│  Version-controlled RDF persistence.              │
│  Accepts any valid RDF. Indifferent to            │
│  interpretation. Branching, committing, diffing.  │
└──────────────────────────────────────────────────┘
```

**Storage** spans Flexo's Layer 0 (Quadstore) and Layer 1 (version-controlled graph management). It stores triples — it doesn't know what a `Complex` or `Edge` means. Flexo's branching, committing, and diffing all operate here.

**Schema** is not a separate architectural layer in Flexo — ontology triples live in the same quadstore as instance data. But it is a distinct service concern: the vocabulary and structure that give data its meaning. Ontology packages are modular — a core package defines abstract types, domain packages extend them. This is analogous to package management: import what you need, compose without conflict as long as namespaces don't collide.

**Verification** checks whether a model state satisfies the constraints declared by the schema packages. This is where SHACL shape validation and SPARQL constraint queries execute. In a production architecture, this service could **gate commits** — rejecting changes that would put a branch into a non-compliant state. Currently implemented client-side (pyshacl + rdflib); a hosted verification service is the natural next step.

### How These Concerns Map to Flexo's Architectural Layers

| Concern | Flexo Layer(s) | Current implementation | Future |
| --- | --- | --- | --- |
| Storage | Layer 0 (Quadstore) + Layer 1 (MMS core) | Flexo as-is | Flexo as-is |
| Schema | Stored in Layer 0, interpreted by clients (Layer 3) | Ontology files loaded as RDF; no server-side reasoning | Server-side ontology registry / package manager |
| Verification | Currently Layer 3 (client-side) | pyshacl + rdflib in verify.py | Hosted service between Layer 1 and Layer 2 |

## KC ↔ SysML v2 Correspondence

The Knowledge Complex stack used in this experiment mirrors the SysML v2 concern structure at smaller scale, making the pattern legible in a single experiment run:

| KC Stack (this experiment) | SysML v2 Stack (future experiment) |
| --- | --- |
| Flexo Layer 0+1 — version-controlled RDF | Flexo Layer 0+1 — version-controlled RDF |
| KC Core ontology (Element, Vertex, Edge, Face, Complex, boundedBy) | KerML (core modeling abstractions: features, types, relationships) |
| MTG Domain ontology (Color, ColorPair, ColorTriple, guild, theme...) | SysML v2 domain/discipline extensions (mechanical, electrical, thermal...) |
| SHACL shapes (boundary-closure, cardinality, triangle) | KerML/SysML v2 compiler checks + constraint verification services |
| Client-side pyshacl + SPARQL oracle | Hosted verification service (when available) |

The KC stack comprises 6 classes, 2 object properties, ~15 datatype properties, and 6 SHACL shapes. When KerML and SysML v2 compiler/verification services become available, a parallel experiment should demonstrate the same three-concern pattern at full SysML scale.

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

1. **Storage accepts everything**: The quadstore stores instance data, ontology triples, and SHACL shapes identically — they're all just RDF. It also stores cross-application states that violate constraints, without complaint.

2. **Schema is modular**: The ontology is split into composable packages loaded sequentially. The core package provides the topological backbone; the domain package extends it with MTG-specific types and properties. Each package brings its own SHACL shapes.

3. **Verification detects what storage cannot**: The client-side verification service fetches triples from Flexo via SPARQL CONSTRUCT, loads the schema packages, runs SHACL validation and oracle queries, and reports pass/fail. It validates the ancestor and individual commits (PASS), then catches the invalid merged states (FAIL).

4. **The conflict scenario is the proof**: No synthetic bad data is needed. The cross-application states are syntactically valid RDF that storage happily accepts — but they fail verification. The merge conflicts naturally demonstrate why all three concerns are necessary.

## Prerequisites

- A pre-issued Bearer token for the remote Layer 1 service at `try-layer1.starforge.app`
- Python 3.8+ with `rdflib` and `pyshacl`:
  ```bash
  pip install -r requirements.txt
  ```
- `curl` on PATH

The experiment can also run against a local Flexo instance by overriding `FLEXO_BASE_URL`:

```bash
export FLEXO_BASE_URL=http://localhost:8080
```

Note: local Flexo on Apple Silicon runs under QEMU emulation and is significantly slower (repo creation alone can take 10-15 minutes).

## Running

```bash
# Set your Bearer token
export FLEXO_TOKEN="eyJhbGci..."

# Run the experiment
cd experiments/experiment-12
./run.sh
```

Each run creates a unique repo name (timestamped) so there's no stale state to worry about.

Expected runtime: ~1-2 minutes against the remote server.

## Expected Results

| Branch | Storage | Verification (SHACL) | Verification (Oracle) | Notes |
| --- | --- | --- | --- | --- |
| master (ancestor) | Accepted | PASS | PASS | All 25 elements valid |
| branch-a (commit u) | Accepted | PASS | PASS | BG + dependent faces removed |
| branch-b (commit v) | Accepted | PASS | PASS | BG/BRG enriched with properties |
| branch-uv (u then v) | Accepted | PASS | **FAIL** (4 orphans) | Orphaned properties on deleted elements |
| branch-vu (v then u) | Accepted | PASS | PASS | Wildcard DELETE cleaned everything |

The key finding: storage accepted all five states. Only verification can distinguish valid from invalid. And the two cross-application orderings produce *different* results — branch-uv fails (orphaned properties) while branch-vu passes (wildcard DELETE caught everything). The conflict is non-commutative: application order matters for the residual data state.

## File Manifest

| File | Concern | Description |
| --- | --- | --- |
| `run.sh` | Orchestrator | Main script — exercises all three concerns |
| `verify.py` | Verification | Client-side verification service (pyshacl + rdflib SPARQL) |
| `ontology/kc-core/ontology.ttl` | Schema | KC core OWL ontology |
| `ontology/kc-core/shapes.ttl` | Schema | KC core SHACL shapes |
| `ontology/mtg-domain/ontology.ttl` | Schema | MTG domain OWL extension |
| `ontology/mtg-domain/shapes.ttl` | Schema | MTG domain SHACL shapes |
| `instance/ancestor-model.ttl` | Storage | Pure instance data (25 MTG elements) |
| `commits/commit-u-remove-bg.ru` | Storage | SPARQL UPDATE: remove BG + dependent faces |
| `commits/commit-v-enrich-bg.ru` | Storage | SPARQL UPDATE: enrich BG/BRG properties |
| `oracle/*.rq` | Verification | SPARQL constraint queries (C1–C6) |
| `requirements.txt` | — | Python dependencies |
